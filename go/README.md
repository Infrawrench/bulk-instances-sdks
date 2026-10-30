# bulkinstances

AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full
history, from the bundles Infrawrench publishes at `instances-bundles.infrawrench.com`.

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

## Other AWS platforms

`DownloadAWSPricingData(ctx, platform, opts)` loads any platform's bundle;
`DownloadAWSEC2PricingData(ctx, opts)` is the same as `DownloadAWSPricingData(ctx, "ec2", opts)`.
`AWSPlatforms` lists the platforms:

| Platform | AWS service |
| --- | --- |
| `ec2` | EC2 |
| `rds` | RDS |
| `elasticache` | ElastiCache |
| `opensearch` | OpenSearch Service |
| `redshift` | Redshift |
| `docdb` | DocumentDB |
| `neptune` | Neptune |
| `memorydb` | MemoryDB |
| `dax` | DynamoDB Accelerator |
| `sagemaker` | SageMaker |
| `emr` | EMR |
| `gamelift` | GameLift |

The fields that pick a price differ by platform. `data.VariantKeys()` names them, and every
price's `Fields` map is keyed by them:

```go
rds, err := bulkinstances.DownloadAWSPricingData(context.Background(), "rds", bulkinstances.Options{})
if err != nil {
	log.Fatal(err)
}
fmt.Println(rds.VariantKeys()) // [databaseEngine databaseEdition licenseModel deploymentOption ...]
db, ok := rds.Get("db.m5.large")
if !ok {
	log.Fatal("no db.m5.large")
}
for _, p := range db.Pricing().OnDemand {
	if p.RegionCode == "us-east-1" && p.Fields["databaseEngine"] == "MySQL" &&
		p.Fields["deploymentOption"] == "Multi-AZ" {
		fmt.Println(p.Hourly)
	}
}
```

`OperatingSystem`, `Tenancy`, `LicenseModel`, `PreInstalledSW` and `Capacitystatus` are EC2's
variant fields. On other platforms they are `""`, unless the platform has a field with that name
(RDS has `licenseModel`).

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`CachePath`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Each platform's bundle is cached
under its own name (`rds-bundle-…json`), so loading one never evicts another. Set
`DisableCache: true` to always download and never touch the disk.

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
