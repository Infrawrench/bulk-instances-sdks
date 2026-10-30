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

func main() {
	baseURL, cachePath, token, cache := os.Args[1], os.Args[2], os.Args[3], os.Args[4]
	opts := bulkinstances.Options{BaseURL: baseURL, CachePath: cachePath, DisableCache: cache != "1"}
	if token != "-" {
		opts.Token = token
	}
	var data *bulkinstances.AWSPricingData
	var err error
	if len(os.Args) > 5 {
		data, err = bulkinstances.DownloadAWSPricingData(context.Background(), os.Args[5], opts)
	} else {
		data, err = bulkinstances.DownloadAWSEC2PricingData(context.Background(), opts)
	}
	if err != nil {
		var e *bulkinstances.Error
		if errors.As(err, &e) {
			out, _ := json.Marshal(obj{"error": obj{"status": nullable(e.Status), "message": e.Error()}})
			fmt.Println(string(out))
			os.Exit(3)
		}
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	snapshots := []int64{}
	for _, s := range data.Snapshots() {
		snapshots = append(snapshots, ts(s))
	}
	regions := data.Regions()
	locations := append(slices.Sorted(maps.Keys(regions)), "Mystery", "Nowhere")
	keys := data.Keys()
	slices.Sort(keys)
	_, missing := data.Get("nope")
	var getMissing any
	if missing {
		getMissing = "present"
	}
	instances := obj{}
	for _, k := range data.Keys() {
		i, _ := data.Get(k)
		var deletedAt any
		if t, ok := i.DeletedAt(); ok {
			deletedAt = ts(t)
		}
		in := obj{}
		for _, r := range locations {
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
		instances[k] = obj{
			"name": i.Name, "createdAt": ts(i.CreatedAt()), "deletedAt": deletedAt,
			"attributes": i.Attributes(), "attributesIn": in, "attributesHistory": history,
			"pricing":        obj{"onDemand": od, "reserved": rs},
			"pricingHistory": obj{"onDemand": hod, "reserved": hrs},
		}
	}
	out, err := json.MarshalIndent(obj{
		"offer": data.Offer(), "variantKeys": data.VariantKeys(),
		"snapshots": snapshots, "regions": regions, "keys": keys,
		"has":        obj{"m5.large": data.Has("m5.large"), "nope": data.Has("nope")},
		"getMissing": getMissing, "instances": instances,
	}, "", " ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(string(out))
}
