# bulkinstances

AWS EC2 instance attributes and prices, with their full history, from the bundle
Infrawrench publishes at `instances-bundles.infrawrench.com`.

```sh
go get github.com/infrawrench/bulk-instances-sdks/go
```

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	bulkinstances "github.com/infrawrench/bulk-instances-sdks/go"
)

func main() {
	data, err := bulkinstances.DownloadAWSEC2PricingData(context.Background(), bulkinstances.Options{
		Token: os.Getenv("INFRAWRENCH_API_KEY"),
	})
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println(data.Keys()) // [m5.large t2.micro ...]

	m5, ok := data.Get("m5.large")
	if !ok {
		log.Fatal("no m5.large")
	}
	fmt.Println(m5.Attributes()["vcpu"])                  // 2
	fmt.Println(m5.AttributesIn("US East (N. Virginia)")) // with that region's overrides
	for _, p := range m5.Pricing().OnDemand {
		if p.RegionCode == "us-east-1" && p.OperatingSystem == "Linux" && p.Tenancy == "Shared" &&
			p.PreInstalledSW == "NA" && p.Capacitystatus == "Used" {
			fmt.Println(p.Hourly) // 0.096
		}
	}

	history := m5.AttributesHistory()        // every attribute change, oldest first
	reserved := m5.PricingHistory().Reserved // every reserved price change, oldest first
	fmt.Println(len(history), len(reserved))
}
```

Any Infrawrench bearer credential works as `Token` (an `iwk_` API key, an agent
credential or a WorkOS access token). It defaults to `INFRAWRENCH_API_KEY`.

Failures to download come back as a `*bulkinstances.Error`, whose `Status` is the
HTTP status (401 for a rejected token), or 0 when there was no response.

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`CachePath`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Set `DisableCache: true`
to always download and never touch the disk.

Loading decompresses and parses the whole bundle. Instances are decoded lazily:
`Get` only wraps the raw rows, and `Attributes`, `AttributesHistory`, `Pricing`
and `PricingHistory` each decode on first call and keep the result. The
returned slices and maps are shared between calls, so treat them as read-only.
The data is safe for concurrent use.

## Prices and regions

- `Region` is the AWS location name (`US East (N. Virginia)`), `RegionCode` its
  code (`us-east-1`) where the price list gives one, and `""` otherwise.
- `Pricing` holds only what is still offered. In `PricingHistory`, a nil
  `Hourly` means the price stopped being offered at `At`.
- Instances AWS no longer lists are still in `Keys()`, with `DeletedAt` set and
  empty `Pricing`.
