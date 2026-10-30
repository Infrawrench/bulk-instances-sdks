package bulkinstances

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"maps"
	"math"
	"slices"
	"strconv"
	"strings"
	"sync"
	"time"
)

// EC2VariantKeys are the variant keys of EC2 bundles, which don't list their own.
var EC2VariantKeys = []string{"operatingSystem", "tenancy", "licenseModel", "preInstalledSw", "capacitystatus"}

// Variant holds the product fields that pick a price.
type Variant struct {
	// Fields holds every field that picks the price, keyed by name: for RDS,
	// "databaseEngine", "deploymentOption" and so on. [AWSPricingData.VariantKeys]
	// gives their order.
	Fields map[string]string

	// EC2's variant fields. For other platforms these are "" unless the platform
	// shares the field.
	OperatingSystem string
	Tenancy         string
	LicenseModel    string
	PreInstalledSW  string
	Capacitystatus  string
}

// ReservedTerm holds the fields that pick a reserved price.
type ReservedTerm struct {
	LeaseContractLength string
	OfferingClass       string
	PurchaseOption      string
}

// Location is an AWS location.
type Location struct {
	// Region is the AWS location name, e.g. "US East (N. Virginia)".
	Region string
	// RegionCode is e.g. "us-east-1". It is "" for locations the price list never gave a code.
	RegionCode string
}

// OnDemandPrice is a current on-demand price.
type OnDemandPrice struct {
	Location
	Variant
	// Hourly is in USD per hour.
	Hourly float64
	// Since is when this price took effect.
	Since time.Time
}

// ReservedPrice is a current reserved price.
type ReservedPrice struct {
	Location
	Variant
	ReservedTerm
	// Hourly is in USD per hour.
	Hourly float64
	// Upfront is in USD paid up front.
	Upfront float64
	Since   time.Time
}

// Pricing holds the current price of everything still offered.
type Pricing struct {
	OnDemand []OnDemandPrice
	Reserved []ReservedPrice
}

// OnDemandPriceChange is one change to an on-demand price.
type OnDemandPriceChange struct {
	Location
	Variant
	At time.Time
	// Hourly is in USD per hour. nil means no longer offered from At on.
	Hourly *float64
}

// ReservedPriceChange is one change to a reserved price.
type ReservedPriceChange struct {
	Location
	Variant
	ReservedTerm
	At time.Time
	// Hourly is in USD per hour. nil means no longer offered from At on.
	Hourly *float64
	// Upfront is in USD paid up front. nil when Hourly is.
	Upfront *float64
}

// PricingHistory holds every on-demand and reserved price change.
type PricingHistory struct {
	// OnDemand is oldest first.
	OnDemand []OnDemandPriceChange
	// Reserved is oldest first.
	Reserved []ReservedPriceChange
}

// AttributeChange is one change to an instance attribute.
type AttributeChange struct {
	At  time.Time
	Key string
	// Value is nil when the attribute was removed.
	Value *string
	// Region is the AWS location this change applies to, or "" for every region.
	Region string
}

// num is a JSON number that may be null, or missing at the end of a short row.
type num struct {
	v  float64
	ok bool
}

func (n *num) UnmarshalJSON(b []byte) error {
	if string(b) == "null" {
		*n = num{}
		return nil
	}
	v, err := strconv.ParseFloat(string(b), 64)
	if err != nil {
		return fmt.Errorf("%s is not a number", b)
	}
	*n = num{v, true}
	return nil
}

func (n num) String() string {
	if !n.ok {
		return "null"
	}
	return strconv.FormatFloat(n.v, 'g', -1, 64)
}

// ptr returns n as a new *float64, or nil if n is null.
func (n num) ptr() *float64 {
	if !n.ok {
		return nil
	}
	v := n.v
	return &v
}

// at returns row[i], or null if the row is shorter.
func at(row []num, i int) num {
	if i < len(row) {
		return row[i]
	}
	return num{}
}

// index returns n as an index into a slice of length size.
func index(n num, size int) (int, bool) {
	if !n.ok || n.v < 0 || n.v >= float64(size) || n.v != math.Trunc(n.v) {
		return 0, false
	}
	return int(n.v), true
}

// date converts Unix seconds to a UTC time, at millisecond precision.
func date(ts num) time.Time {
	return time.UnixMilli(int64(ts.v * 1000)).UTC()
}

// bundle is the bundle as instances-bundler writes it; every string is an index into table.
type bundle struct {
	// EC2 bundles leave out offer, which stays nil, and variant_keys, which
	// parseBundle sets to EC2VariantKeys.
	offer       *string
	variantKeys []string
	table       []string
	snapshots   []num
	regions     []json.RawMessage
	variants    [][]num
	terms       [][]num
	// keys holds the instance types in bundle order; instances holds each one's raw row.
	keys      []string
	instances map[string][]byte
}

// skip decodes any JSON value into nothing.
type skip struct{}

func (*skip) UnmarshalJSON([]byte) error { return nil }

func expectDelim(dec *json.Decoder, want json.Delim) error {
	tok, err := dec.Token()
	if err != nil {
		return err
	}
	if tok != want {
		return fmt.Errorf("got %v, want %v", tok, want)
	}
	return nil
}

// parseBundle parses the whole bundle. The instances are only located, as slices
// of b, which nothing modifies after this.
func parseBundle(b []byte) (*AWSPricingData, error) {
	bd := &bundle{instances: map[string][]byte{}}
	dec := json.NewDecoder(bytes.NewReader(b))
	err := expectDelim(dec, '{')
	for err == nil && dec.More() {
		var tok json.Token
		if tok, err = dec.Token(); err != nil {
			break
		}
		switch tok {
		case "offer":
			err = dec.Decode(&bd.offer)
		case "variant_keys":
			err = dec.Decode(&bd.variantKeys)
		case "compression_table":
			err = dec.Decode(&bd.table)
		case "snapshots":
			err = dec.Decode(&bd.snapshots)
		case "regions":
			err = dec.Decode(&bd.regions)
		case "variants":
			err = dec.Decode(&bd.variants)
		case "reserved_terms":
			err = dec.Decode(&bd.terms)
		case "instances":
			err = bd.parseInstances(dec, b)
		default:
			err = dec.Decode(&skip{})
		}
	}
	if err == nil {
		err = expectDelim(dec, '}')
	}
	if err == nil {
		if _, end := dec.Token(); end != io.EOF {
			err = errors.New("unexpected data after the bundle")
		}
	}
	if err == nil {
		err = bd.checkVariants()
	}
	if err != nil {
		return nil, fmt.Errorf("bulkinstances: parsing the bundle: %w", err)
	}
	return newAWSPricingData(bd), nil
}

// checkVariants defaults the variant keys to EC2's and checks that every variant has
// one field per key.
func (bd *bundle) checkVariants() error {
	if bd.variantKeys == nil {
		bd.variantKeys = slices.Clone(EC2VariantKeys)
	}
	for _, row := range bd.variants {
		if len(row) != len(bd.variantKeys) {
			return fmt.Errorf("variant has %d fields, expected %d", len(row), len(bd.variantKeys))
		}
	}
	return nil
}

func (bd *bundle) parseInstances(dec *json.Decoder, b []byte) error {
	bd.keys, bd.instances = nil, map[string][]byte{}
	if err := expectDelim(dec, '{'); err != nil {
		return err
	}
	for dec.More() {
		tok, err := dec.Token()
		if err != nil {
			return err
		}
		key := tok.(string)
		start := dec.InputOffset()
		if err := dec.Decode(&skip{}); err != nil {
			return err
		}
		// From just after the key: drop the colon and whitespace before the value.
		raw := bytes.TrimLeft(b[start:dec.InputOffset()], " \t\r\n:")
		if _, dup := bd.instances[key]; !dup {
			bd.keys = append(bd.keys, key)
		}
		bd.instances[key] = raw
	}
	return expectDelim(dec, '}')
}

// decodeTuple decodes the JSON array b into dsts in order, ignoring extra elements.
func decodeTuple(b []byte, dsts ...any) error {
	dec := json.NewDecoder(bytes.NewReader(b))
	if err := expectDelim(dec, '['); err != nil {
		return err
	}
	for i, dst := range dsts {
		if !dec.More() {
			return fmt.Errorf("%d elements, want %d", i, len(dsts))
		}
		if err := dec.Decode(dst); err != nil {
			return err
		}
	}
	return nil
}

// AWSPricingData is one AWS platform's pricing data, keyed by instance type.
//
// Nothing is decoded until it is asked for: Get wraps the raw rows, and each
// method of the returned [AWSInstance] decodes its part on first call and keeps
// the result.
type AWSPricingData struct {
	raw      *bundle
	mu       sync.Mutex
	wrapped  map[string]*AWSInstance
	regions  func() map[string]map[string]string
	variants func() []Variant
	terms    func() []ReservedTerm
}

func newAWSPricingData(raw *bundle) *AWSPricingData {
	d := &AWSPricingData{raw: raw, wrapped: map[string]*AWSInstance{}}
	d.regions = sync.OnceValue(d.decodeRegions)
	d.variants = sync.OnceValue(d.decodeVariants)
	d.terms = sync.OnceValue(d.decodeTerms)
	return d
}

// Keys returns every instance type in the bundle, in bundle order, including ones
// AWS no longer lists (see [AWSInstance.DeletedAt]).
func (d *AWSPricingData) Keys() []string {
	return slices.Clone(d.raw.keys)
}

// Has reports whether the bundle has ever listed this instance type.
func (d *AWSPricingData) Has(instanceType string) bool {
	_, ok := d.raw.instances[instanceType]
	return ok
}

// Get returns the instance with this type (e.g. "m5.large"), or false if the
// bundle has never listed it.
func (d *AWSPricingData) Get(instanceType string) (*AWSInstance, bool) {
	raw, ok := d.raw.instances[instanceType]
	if !ok {
		return nil, false
	}
	d.mu.Lock()
	defer d.mu.Unlock()
	inst := d.wrapped[instanceType]
	if inst == nil {
		inst = newAWSInstance(instanceType, raw, d)
		d.wrapped[instanceType] = inst
	}
	return inst, true
}

// Offer returns the AWS offer code, e.g. "AmazonEC2" or "AmazonRDS".
func (d *AWSPricingData) Offer() string {
	if d.raw.offer == nil {
		return "AmazonEC2"
	}
	return *d.raw.offer
}

// VariantKeys returns the names of the fields that pick a price, which every
// price's [Variant.Fields] is keyed by. EC2 bundles have [EC2VariantKeys].
func (d *AWSPricingData) VariantKeys() []string {
	return slices.Clone(d.raw.variantKeys)
}

// Snapshots returns the publication date of every AWS price list in the bundle,
// oldest first.
func (d *AWSPricingData) Snapshots() []time.Time {
	out := make([]time.Time, len(d.raw.snapshots))
	for i, ts := range d.raw.snapshots {
		out[i] = date(ts)
	}
	return out
}

// Regions returns the attributes of each AWS location ("regionCode",
// "locationType"), keyed by location name.
func (d *AWSPricingData) Regions() map[string]map[string]string {
	return d.regions()
}

func (d *AWSPricingData) decodeRegions() map[string]map[string]string {
	out := make(map[string]map[string]string, len(d.raw.regions))
	for _, row := range d.raw.regions {
		var loc num
		var pairs [][]num
		if err := decodeTuple(row, &loc, &pairs); err != nil {
			panic(fmt.Sprintf("bulkinstances: malformed region %s: %v", row, err))
		}
		attrs := make(map[string]string, len(pairs))
		for _, kv := range pairs {
			attrs[d.str(at(kv, 0))] = d.str(at(kv, 1))
		}
		out[d.str(loc)] = attrs
	}
	return out
}

func (d *AWSPricingData) decodeVariants() []Variant {
	out := make([]Variant, len(d.raw.variants))
	for i, row := range d.raw.variants {
		// parseBundle checked that every row has one field per key.
		fields := make(map[string]string, len(row))
		for j, k := range d.raw.variantKeys {
			fields[k] = d.str(row[j])
		}
		// A missing field reads as "".
		out[i] = Variant{
			Fields:          fields,
			OperatingSystem: fields["operatingSystem"],
			Tenancy:         fields["tenancy"],
			LicenseModel:    fields["licenseModel"],
			PreInstalledSW:  fields["preInstalledSw"],
			Capacitystatus:  fields["capacitystatus"],
		}
	}
	return out
}

func (d *AWSPricingData) decodeTerms() []ReservedTerm {
	out := make([]ReservedTerm, len(d.raw.terms))
	for i, row := range d.raw.terms {
		out[i] = ReservedTerm{
			LeaseContractLength: d.str(at(row, 0)),
			OfferingClass:       d.str(at(row, 1)),
			PurchaseOption:      d.str(at(row, 2)),
		}
	}
	return out
}

func (d *AWSPricingData) str(i num) string {
	j, ok := index(i, len(d.raw.table))
	if !ok {
		panic(fmt.Sprintf("bulkinstances: string index %v out of range", i))
	}
	return d.raw.table[j]
}

func (d *AWSPricingData) location(i num) Location {
	region := d.str(i)
	return Location{Region: region, RegionCode: d.regions()[region]["regionCode"]}
}

func (d *AWSPricingData) variant(i num) Variant {
	vs := d.variants()
	j, ok := index(i, len(vs))
	if !ok {
		panic(fmt.Sprintf("bulkinstances: variant index %v out of range", i))
	}
	return vs[j]
}

func (d *AWSPricingData) term(i num) ReservedTerm {
	ts := d.terms()
	j, ok := index(i, len(ts))
	if !ok {
		panic(fmt.Sprintf("bulkinstances: reserved term index %v out of range", i))
	}
	return ts[j]
}

// rawInstance is one instance's row in the bundle.
type rawInstance struct {
	attrs     [][]num
	changes   [][]num
	basePrice num
	onDemand  [][]num
	reserved  [][]num
	createdAt num
	deletedAt num
}

// AWSInstance is one instance type. Each method decodes on first call and keeps
// the result.
type AWSInstance struct {
	// Name is the instance type, e.g. "m5.large".
	Name string

	data              *AWSPricingData
	raw               func() *rawInstance
	attributes        func() map[string]string
	attributesHistory func() []AttributeChange
	pricing           func() Pricing
	pricingHistory    func() PricingHistory
}

func newAWSInstance(name string, raw []byte, data *AWSPricingData) *AWSInstance {
	i := &AWSInstance{Name: name, data: data}
	i.raw = sync.OnceValue(func() *rawInstance {
		var r rawInstance
		err := decodeTuple(raw, &r.attrs, &r.changes, &r.basePrice, &r.onDemand, &r.reserved, &r.createdAt, &r.deletedAt)
		if err != nil {
			panic(fmt.Sprintf("bulkinstances: malformed instance %q: %v", name, err))
		}
		return &r
	})
	i.attributes = sync.OnceValue(i.decodeAttributes)
	i.attributesHistory = sync.OnceValue(i.decodeAttributesHistory)
	i.pricing = sync.OnceValue(i.decodePricing)
	i.pricingHistory = sync.OnceValue(i.decodePricingHistory)
	return i
}

// CreatedAt returns the publication date of the first price list that listed this instance.
func (i *AWSInstance) CreatedAt() time.Time {
	return date(i.raw().createdAt)
}

// DeletedAt returns the publication date of the first price list that stopped
// listing it, or false if AWS still lists it.
func (i *AWSInstance) DeletedAt() (time.Time, bool) {
	r := i.raw()
	if !r.deletedAt.ok {
		return time.Time{}, false
	}
	return date(r.deletedAt), true
}

// Attributes returns the latest attributes shared by every region. Regional
// differences are in [AWSInstance.AttributesIn].
func (i *AWSInstance) Attributes() map[string]string {
	return i.attributes()
}

func (i *AWSInstance) decodeAttributes() map[string]string {
	out := map[string]string{}
	for _, c := range i.AttributesHistory() {
		if c.Region != "" {
			continue
		}
		if c.Value == nil {
			delete(out, c.Key)
		} else {
			out[c.Key] = *c.Value
		}
	}
	return out
}

// AttributesIn returns the latest attributes in one AWS location (e.g. "US East
// (N. Virginia)"): the global ones with that region's overrides on top. A regional
// override keeps applying even after a newer global change to the same key.
//
// The returned map is new on every call and belongs to the caller.
func (i *AWSInstance) AttributesIn(region string) map[string]string {
	out := maps.Clone(i.Attributes())
	overrides := map[string]*string{}
	for _, c := range i.AttributesHistory() {
		if c.Region == region {
			overrides[c.Key] = c.Value
		}
	}
	for k, v := range overrides {
		if v == nil {
			delete(out, k)
		} else {
			out[k] = *v
		}
	}
	return out
}

// AttributesHistory returns every attribute change, oldest first, starting with
// the attributes the instance was first listed with.
func (i *AWSInstance) AttributesHistory() []AttributeChange {
	return i.attributesHistory()
}

func (i *AWSInstance) decodeAttributesHistory() []AttributeChange {
	d, r := i.data, i.raw()
	created := i.CreatedAt()
	out := make([]AttributeChange, 0, len(r.attrs)+len(r.changes))
	for _, kv := range r.attrs {
		value := d.str(at(kv, 1))
		out = append(out, AttributeChange{At: created, Key: d.str(at(kv, 0)), Value: &value})
	}
	changes := make([]AttributeChange, 0, len(r.changes))
	for _, row := range r.changes {
		c := AttributeChange{At: date(at(row, 0)), Key: d.str(at(row, 1))}
		if v := at(row, 2); v.ok {
			value := d.str(v)
			c.Value = &value
		}
		if region := at(row, 3); region.ok {
			c.Region = d.str(region)
		}
		changes = append(changes, c)
	}
	// Stable, so rows with the same timestamp keep their order (later rows win).
	slices.SortStableFunc(changes, func(a, b AttributeChange) int { return a.At.Compare(b.At) })
	return append(out, changes...)
}

// Pricing returns the current price of everything still offered.
func (i *AWSInstance) Pricing() Pricing {
	return i.pricing()
}

// priceKey identifies a price by its location and every variant field, in variant-key
// order, so that variants differing only in a field EC2 lacks are kept apart.
func (d *AWSPricingData) priceKey(region string, v Variant) string {
	var b strings.Builder
	b.WriteString(region)
	for _, k := range d.raw.variantKeys {
		b.WriteByte(0)
		b.WriteString(v.Fields[k])
	}
	return b.String()
}

type reservedKey struct {
	price string
	ReservedTerm
}

// latest returns the last row for each key, in order of each key's first row.
func latest[T any, K comparable](rows []T, key func(T) K) []T {
	var out []T
	pos := map[K]int{}
	for _, r := range rows {
		k := key(r)
		if j, ok := pos[k]; ok {
			out[j] = r
		} else {
			pos[k] = len(out)
			out = append(out, r)
		}
	}
	return out
}

func (i *AWSInstance) decodePricing() Pricing {
	d, h := i.data, i.PricingHistory()
	var p Pricing
	for _, c := range latest(h.OnDemand, func(c OnDemandPriceChange) string {
		return d.priceKey(c.Region, c.Variant)
	}) {
		if c.Hourly != nil {
			p.OnDemand = append(p.OnDemand, OnDemandPrice{Location: c.Location, Variant: c.Variant, Hourly: *c.Hourly, Since: c.At})
		}
	}
	for _, c := range latest(h.Reserved, func(c ReservedPriceChange) reservedKey {
		return reservedKey{d.priceKey(c.Region, c.Variant), c.ReservedTerm}
	}) {
		if c.Hourly != nil {
			upfront := 0.0
			if c.Upfront != nil {
				upfront = *c.Upfront
			}
			p.Reserved = append(p.Reserved, ReservedPrice{
				Location: c.Location, Variant: c.Variant, ReservedTerm: c.ReservedTerm,
				Hourly: *c.Hourly, Upfront: upfront, Since: c.At,
			})
		}
	}
	return p
}

// PricingHistory returns every on-demand and reserved price change, oldest first.
func (i *AWSInstance) PricingHistory() PricingHistory {
	return i.pricingHistory()
}

func (i *AWSInstance) decodePricingHistory() PricingHistory {
	d, r := i.data, i.raw()
	h := PricingHistory{
		OnDemand: make([]OnDemandPriceChange, 0, len(r.onDemand)),
		Reserved: make([]ReservedPriceChange, 0, len(r.reserved)),
	}
	// [ts, region, variant, price: omitted = base price, null = no longer offered]
	for _, row := range r.onDemand {
		hourly := r.basePrice
		if len(row) > 3 {
			hourly = row[3]
		}
		h.OnDemand = append(h.OnDemand, OnDemandPriceChange{
			Location: d.location(at(row, 1)), Variant: d.variant(at(row, 2)),
			At: date(at(row, 0)), Hourly: hourly.ptr(),
		})
	}
	// [ts, region, variant, term, hourly: null = no longer offered, upfront: omitted if 0]
	for _, row := range r.reserved {
		c := ReservedPriceChange{
			Location: d.location(at(row, 1)), Variant: d.variant(at(row, 2)), ReservedTerm: d.term(at(row, 3)),
			At: date(at(row, 0)),
		}
		if hourly := at(row, 4); hourly.ok {
			upfront := at(row, 5)
			if !upfront.ok {
				upfront = num{0, true}
			}
			c.Hourly, c.Upfront = hourly.ptr(), upfront.ptr()
		}
		h.Reserved = append(h.Reserved, c)
	}
	byTime := func(a, b time.Time) int { return a.Compare(b) }
	slices.SortStableFunc(h.OnDemand, func(a, b OnDemandPriceChange) int { return byTime(a.At, b.At) })
	slices.SortStableFunc(h.Reserved, func(a, b ReservedPriceChange) int { return byTime(a.At, b.At) })
	return h
}
