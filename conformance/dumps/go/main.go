// Command dump prints the Go SDK's view of a bundle as described in harness/DUMP.md.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"maps"
	"os"
	"slices"
	"time"

	bulkinstances "github.com/infrawrench/bulk-instances-sdks/go"
)

type obj = map[string]any

func ts(t time.Time) int64 { return t.Unix() }

func nullable[T comparable](v T) any {
	var zero T
	if v == zero {
		return nil
	}
	return v
}

func ptr[T any](p *T) any {
	if p == nil {
		return nil
	}
	return *p
}

func loc(l bulkinstances.Location, v bulkinstances.Variant) obj {
	return obj{
		"region": l.Region, "regionCode": nullable(l.RegionCode), "variant": v.Fields,
		"operatingSystem": v.OperatingSystem, "tenancy": v.Tenancy, "licenseModel": v.LicenseModel,
		"preInstalledSw": v.PreInstalledSW, "capacitystatus": v.Capacitystatus,
	}
}

func term(o obj, t bulkinstances.ReservedTerm) obj {
	o["leaseContractLength"] = t.LeaseContractLength
	o["offeringClass"] = t.OfferingClass
	o["purchaseOption"] = t.PurchaseOption
	return o
}

func fail(err error) {
	var e *bulkinstances.Error
	if errors.As(err, &e) {
		out, _ := json.Marshal(obj{"error": obj{"status": nullable(e.Status), "message": e.Error()}})
		fmt.Println(string(out))
		os.Exit(3)
	}
	fmt.Fprintln(os.Stderr, err)
	os.Exit(1)
}

func printJSON(v any) {
	out, err := json.MarshalIndent(v, "", " ")
	if err != nil {
		fail(err)
	}
	fmt.Println(string(out))
}

func dumpInstance(i *bulkinstances.AWSInstance, regionNames []string) obj {
	var deletedAt any
	if t, ok := i.DeletedAt(); ok {
		deletedAt = ts(t)
	}
	in := obj{}
	for _, r := range append(regionNames, "Mystery", "Nowhere") {
		in[r] = i.AttributesIn(r)
	}
	history := []obj{}
	for _, c := range i.AttributesHistory() {
		history = append(history, obj{"at": ts(c.At), "key": c.Key, "value": ptr(c.Value), "region": nullable(c.Region)})
	}
	p, h := i.Pricing(), i.PricingHistory()
	od, rs, hod, hrs := []obj{}, []obj{}, []obj{}, []obj{}
	for _, r := range p.OnDemand {
		o := loc(r.Location, r.Variant)
		o["hourly"], o["since"] = r.Hourly, ts(r.Since)
		od = append(od, o)
	}
	for _, r := range p.Reserved {
		o := term(loc(r.Location, r.Variant), r.ReservedTerm)
		o["hourly"], o["upfront"], o["since"] = r.Hourly, r.Upfront, ts(r.Since)
		rs = append(rs, o)
	}
	for _, r := range h.OnDemand {
		o := loc(r.Location, r.Variant)
		o["hourly"], o["at"] = ptr(r.Hourly), ts(r.At)
		hod = append(hod, o)
	}
	for _, r := range h.Reserved {
		o := term(loc(r.Location, r.Variant), r.ReservedTerm)
		o["hourly"], o["upfront"], o["at"] = ptr(r.Hourly), ptr(r.Upfront), ts(r.At)
		hrs = append(hrs, o)
	}
	return obj{
		"name": i.Name, "createdAt": ts(i.CreatedAt()), "deletedAt": deletedAt,
		"attributes": i.Attributes(), "attributesIn": in, "attributesHistory": history,
		"pricing":        obj{"onDemand": od, "reserved": rs},
		"pricingHistory": obj{"onDemand": hod, "reserved": hrs},
	}
}

func main() {
	baseURL, cachePath, token, cache := os.Args[1], os.Args[2], os.Args[3], os.Args[4]
	if token == "-" {
		token = ""
	}

	if len(os.Args) > 6 {
		apiOpts := bulkinstances.AWSInstanceOptions{Token: token, BaseURL: baseURL}
		// RunPod and Alibaba have their own functions and instance types.
		var i *bulkinstances.AWSInstance
		var err error
		switch platform, name := os.Args[5], os.Args[6]; platform {
		case "runpod":
			var r *bulkinstances.RunpodInstance
			if r, err = bulkinstances.FetchRunpodInstance(context.Background(), name, apiOpts); r != nil {
				i = r.AWSInstance
			}
		case "alibaba":
			var a *bulkinstances.AlibabaInstance
			if a, err = bulkinstances.FetchAlibabaInstance(context.Background(), name, apiOpts); a != nil {
				i = a.AWSInstance
			}
		default:
			i, err = bulkinstances.FetchAWSInstance(context.Background(), platform, name, apiOpts)
		}
		if err != nil {
			fail(err)
		}
		var dumped any
		if i != nil {
			// The regions its attributes are overridden in; every other one is the same as Attributes.
			regions := map[string]bool{}
			for _, c := range i.AttributesHistory() {
				if c.Region != "" {
					regions[c.Region] = true
				}
			}
			dumped = dumpInstance(i, slices.Sorted(maps.Keys(regions)))
		}
		printJSON(obj{"instance": dumped})
		return
	}

	opts := bulkinstances.Options{Token: token, BaseURL: baseURL, CachePath: cachePath, DisableCache: cache != "1"}
	platform := ""
	if len(os.Args) > 5 {
		platform = os.Args[5]
	}
	var data *bulkinstances.AWSPricingData
	// get is the loaded data's own Get: RunPod and Alibaba have their own data and instance types.
	var get func(string) (*bulkinstances.AWSInstance, bool)
	var err error
	switch platform {
	case "runpod":
		var d *bulkinstances.RunpodPricingData
		if d, err = bulkinstances.DownloadRunpodPricingData(context.Background(), opts); err == nil {
			data = d.AWSPricingData
			get = func(k string) (*bulkinstances.AWSInstance, bool) {
				i, ok := d.Get(k) // a *RunpodInstance
				if !ok {
					return nil, false
				}
				return i.AWSInstance, true
			}
		}
	case "alibaba":
		var d *bulkinstances.AlibabaPricingData
		if d, err = bulkinstances.DownloadAlibabaPricingData(context.Background(), opts); err == nil {
			data = d.AWSPricingData
			get = func(k string) (*bulkinstances.AWSInstance, bool) {
				i, ok := d.Get(k) // an *AlibabaInstance
				if !ok {
					return nil, false
				}
				return i.AWSInstance, true
			}
		}
	case "":
		data, err = bulkinstances.DownloadAWSEC2PricingData(context.Background(), opts)
	default:
		data, err = bulkinstances.DownloadAWSPricingData(context.Background(), platform, opts)
	}
	if err != nil {
		fail(err)
	}
	if get == nil {
		get = data.Get
	}

	snapshots := []int64{}
	for _, s := range data.Snapshots() {
		snapshots = append(snapshots, ts(s))
	}
	regions := data.Regions()
	keys := data.Keys()
	slices.Sort(keys)
	_, missing := get("nope")
	var getMissing any
	if missing {
		getMissing = "present"
	}
	instances := obj{}
	for _, k := range data.Keys() {
		i, _ := get(k)
		instances[k] = dumpInstance(i, slices.Sorted(maps.Keys(regions)))
	}
	printJSON(obj{
		"offer": data.Offer(), "variantKeys": data.VariantKeys(),
		"snapshots": snapshots, "regions": regions, "keys": keys,
		"has":        obj{"m5.large": data.Has("m5.large"), "nope": data.Has("nope")},
		"getMissing": getMissing, "instances": instances,
	})
}
