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
| `spot` | EC2 Spot (see below) |

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

`spot` is EC2's spot prices. They are in `Pricing().OnDemand`, one per region and `OperatingSystem` (`Linux` or
`Windows`): the lowest price across the region's availability zones, as AWS's Spot pricing page shows it.
Its locations are region codes, so `Region` and `RegionCode` are both `us-east-1`. Spot instances
have no attributes; take their specs from `ec2`. The history goes back to August 2026, hourly at
first and every 6 hours since November 2026, and prices change far more often than on-demand prices.

## RunPod

`DownloadRunpodPricingData(ctx, opts)` loads RunPod's GPU and CPU pod prices. It takes the same `Options` as
the AWS functions, caches the same way, and fails with a `*bulkinstances.Error` like them. It returns a
`*RunpodPricingData`, whose `Get` returns a `*RunpodInstance`; they embed `*AWSPricingData` and `*AWSInstance`,
so they have the same methods.

```go
runpod, err := bulkinstances.DownloadRunpodPricingData(context.Background(), bulkinstances.Options{})
if err != nil {
	log.Fatal(err)
}
h100, ok := runpod.Get("NVIDIA H100 80GB HBM3")
if !ok {
	log.Fatal("no H100")
}
for _, p := range h100.Pricing().OnDemand {
	if p.Fields["cloudType"] == "Secure Cloud" {
		fmt.Println(p.Hourly)
	}
}
```

It has GPU types by RunPod's id (`NVIDIA H100 80GB HBM3`), priced per GPU per hour, and CPU pods by pod id
(`cpu3c-2-4`: flavor, vCPUs, GB of memory), priced per pod per hour; the `productFamily` attribute is `GPU` or
`CPU`. Prices are the same in every data center, so every price is in the location `global`. The only variant
key is `cloudType`, `Secure Cloud` or `Community Cloud`. Savings plans are in `Pricing().Reserved` with the term
`3mo` or `6mo`, `Savings Plan`, `All Upfront`, and `Hourly` is the plan's effective hourly rate. Stock levels
and spot prices are not included. The history starts in November 2026.

`FetchRunpodInstance(ctx, id, opts)` fetches one GPU type or CPU pod from the Infrawrench API instead (see
[One instance](#one-instance)). It returns a `*RunpodInstance`, or `nil` with no error if RunPod has no instance
with that id:

```go
h100, err := bulkinstances.FetchRunpodInstance(ctx, "NVIDIA H100 80GB HBM3", bulkinstances.AWSInstanceOptions{})
```

## Alibaba Cloud

`DownloadAlibabaPricingData(ctx, opts)` loads Alibaba Cloud ECS prices. It takes the same `Options` as the AWS
functions, caches the same way, and fails with a `*bulkinstances.Error` like them. It returns an
`*AlibabaPricingData`, whose `Get` returns an `*AlibabaInstance`; they embed `*AWSPricingData` and
`*AWSInstance`, so they have the same methods.

```go
alibaba, err := bulkinstances.DownloadAlibabaPricingData(context.Background(), bulkinstances.Options{})
if err != nil {
	log.Fatal(err)
}
g6, ok := alibaba.Get("ecs.g6.large")
if !ok {
	log.Fatal("no ecs.g6.large")
}
for _, p := range g6.Pricing().OnDemand {
	if p.RegionCode == "cn-hangzhou" && p.Fields["operatingSystem"] == "Linux" && p.Fields["networkType"] == "VPC" {
		fmt.Println(p.Hourly)
	}
}
```

Its locations are region ids (`cn-hangzhou`), so `Region` and `RegionCode` are the same, and `Regions()` gives
each an English `name`. Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `networkType` (`VPC`,
or `Classic` in older history). `Pricing().OnDemand` has pay-as-you-go prices. `Pricing().Reserved` has
subscriptions, with the term `1mo` or `1yr` to `5yr`, `Subscription`, `All Upfront`: they are paid in full when
bought, so `Hourly` is 0 and `Upfront` is the price. It also has reserved instances, with the term `1yr` or
`3yr`, `Reserved Instance`, and a purchase option. Attributes are Alibaba's instance type definitions
(`CpuCoreCount`, `MemorySize`, `CpuOptions.ThreadsPerCore`, ...), from May 2023 on. The history starts in
May 2018.

`FetchAlibabaInstance(ctx, instanceType, opts)` fetches one instance type from the Infrawrench API instead (see
[One instance](#one-instance)). It returns an `*AlibabaInstance`, or `nil` with no error if Alibaba has no
instance type with that name:

```go
g6, err := bulkinstances.FetchAlibabaInstance(ctx, "ecs.g6.large", bulkinstances.AWSInstanceOptions{})
```

## Azure

`DownloadAzurePricingData(ctx, opts)` loads Azure virtual machine prices. It takes the same `Options` as the AWS
functions, caches the same way, and fails with a `*bulkinstances.Error` like them. It returns an
`*AzurePricingData`, whose `Get` returns an `*AzureInstance`; they embed `*AWSPricingData` and
`*AWSInstance`, so they have the same methods.

```go
azure, err := bulkinstances.DownloadAzurePricingData(context.Background(), bulkinstances.Options{})
if err != nil {
	log.Fatal(err)
}
d2, ok := azure.Get("Standard_D2s_v3")
if !ok {
	log.Fatal("no Standard_D2s_v3")
}
for _, p := range d2.Pricing().OnDemand {
	if p.RegionCode == "eastus" && p.Fields["operatingSystem"] == "Linux" && p.Fields["priority"] == "Regular" {
		fmt.Println(p.Hourly)
	}
}
```

It has VM sizes by ARM name (`Standard_D2s_v3`), priced per VM per hour. Its locations are ARM region names
(`eastus`), so the location and its region code are the same, and `Regions()` gives each Azure's display
`name` (`US East`). Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `priority` (`Regular`,
`Spot` or `Low Priority`). `Pricing().OnDemand` has pay-as-you-go prices, dated by when Azure says they took
effect. `Pricing().Reserved` has reservations, with the term `1yr`, `3yr` or `5yr`, `Reserved Instance`,
`All Upfront`: `Hourly` is 0 and `Upfront` is the whole term's price. Azure lists reservations under `Linux`
only; on Windows the license is billed on top. It also has savings plans, with the term `1yr` or `3yr`,
`Savings Plan`, `No Upfront`, and `Hourly` is the plan's rate. Attributes are `skuName`, `productName` and,
from Azure's pricing calculator, `cores`, `ram` (GB), `diskSize` (temporary disk, GB), `gpu` and `series`.
About a third of sizes, mostly the newest and retired series, have no calculator specs. Dedicated hosts are
not included. The history starts in November 2026.

## Google Cloud

`DownloadGCPPricingData(ctx, opts)` loads Google Cloud Compute Engine prices. It takes the same `Options` as the AWS
functions, caches the same way, and fails with a `*bulkinstances.Error` like them. It returns a
`*GCPPricingData`, whose `Get` returns a `*GCPInstance`; they embed `*AWSPricingData` and
`*AWSInstance`, so they have the same methods.

```go
gcp, err := bulkinstances.DownloadGCPPricingData(context.Background(), bulkinstances.Options{})
if err != nil {
	log.Fatal(err)
}
n2, ok := gcp.Get("n2-standard-2")
if !ok {
	log.Fatal("no n2-standard-2")
}
for _, p := range n2.Pricing().OnDemand {
	if p.RegionCode == "us-central1" && p.Fields["provisioningModel"] == "Standard" {
		fmt.Println(p.Hourly)
	}
}
```

It has machine types by name (`n2-standard-2`), priced per VM per hour. Google bills most machine types per
vCPU and per GiB of memory at their family's rates, plus their GPUs, so each price is worked out from those
rates and the machine type's shape. Prices leave out bundled Local SSD, OS licenses and sustained use
discounts, and TPU, X4, X5 and A4X machine types aren't included. Its locations are regions (`us-central1`),
so the location and its region code are the same. The only variant key is `provisioningModel`, `Standard` or
`Spot`. `Pricing().Reserved` has committed use discounts, with the term `1yr` or `3yr`, `Committed Use`,
`No Upfront`, and `Hourly` is the commitment's rate. Attributes are the machine type's fields from the Compute
Engine API (`guestCpus`, `memoryMb`, `description`, `isSharedCpu`, ...), `acceleratorType` and
`acceleratorCount` for its GPUs, and `zones`, the zones in each region that have it, which differ by region
(see `AttributesIn(region)`). The history starts in November 2026.

## Hetzner, OVHcloud, Oracle Cloud and IBM Cloud

These load the same way as Google Cloud's, with the same options, caching and failures. Each returns its own data and
instance types, which have the same members as the AWS ones.

| Function | Data | Instance |
| --- | --- | --- |
| `DownloadHetznerPricingData` | `HetznerPricingData` | `HetznerInstance` |
| `DownloadHetznerAuctionPricingData` | `HetznerAuctionPricingData` | `HetznerAuctionInstance` |
| `DownloadOVHPricingData` | `OVHPricingData` | `OVHInstance` |
| `DownloadOVHEcoPricingData` | `OVHEcoPricingData` | `OVHEcoInstance` |
| `DownloadOraclePricingData` | `OraclePricingData` | `OracleInstance` |
| `DownloadIBMPricingData` | `IBMPricingData` | `IBMInstance` |

```go
hetzner, err := bulkinstances.DownloadHetznerPricingData(context.Background(), bulkinstances.Options{})
if err != nil {
	log.Fatal(err)
}
server, ok := hetzner.Get("cx23")
if !ok {
	log.Fatal("no cx23")
}
for _, p := range server.Pricing().OnDemand {
	if p.RegionCode == "fsn1" && p.Fields["ipv4"] == "Primary IPv4" {
		fmt.Println(p.Hourly)
	}
}
```

- **`hetzner`**, Hetzner cloud servers, by Cloud API name (`cx23`), per hour. Locations are Cloud API location names (`fsn1`, `ash`). The only variant key is `ipv4`, `IPv6 only` or `Primary IPv4`, since a primary IPv4 is optional and billed apart. `Pricing().Reserved` has the monthly cap, with the term `1mo`, `Monthly Cap`, `Postpaid`, `hourly` 0 and `upfront` the cap. Attributes include `cores`, `cpu`, `memoryInGb`, `diskInGb` and `architecture`.
- **`hetznerauction`**, Hetzner Server Auction listings, by listing id (`3107671`). Each is one physical server, so its history runs from when it is listed until it is sold, and it has the same variant key and term as `hetzner`. Attributes are the listing's hardware and details (`CPU.Name`, `RAM.Size`, `datacenter`, `fixedPrice`, `setupFee`, ...). The bundle is read hourly, so a price drop is dated by the read that saw it.
- **`ovh`**, OVHcloud Public Cloud flavors (`b3-8`), per hour, from the World and US catalogs, in USD. Locations are pricing zones, not regions: `world`, `3az`, `lz-eu`, `lz-eurozone`, `lz-af`, `us` and `us-east-lz-dal-a`. The only variant key is `operatingSystem`. `Pricing().Reserved` has monthly plans where a flavor has them, with the term `1mo`, `Monthly`, `Postpaid` or `All Upfront`, `hourly` 0 and `upfront` the month's price.
- **`ovheco`**, OVHcloud's Kimsufi, So you Start, Rise and Advance servers (`24sys01`), by data center (`gra`, `sgp`); the `range` attribute says which. **These have no on-demand prices**, because they are only rented by the month. The rent is in `Pricing().Reserved`, with the term `1mo`, `Rental`, `All Upfront`, `hourly` 0 and `upfront` the rent, beside prepaying (`1yr` or `2yr`, `Prepaid`). The variant keys are `memory`, `storage` and `systemStorage`, which is often empty.
- **`oracle`**, Oracle Cloud VM and bare metal shapes, per hour, the same in every commercial region, so every price is in `global`. The only variant key is `operatingSystem`. Flexible shapes have no one price, so they are priced at a set of sizes named `<shape>-<ocpus>-<GB>` (`VM.Standard.E5.Flex-2-16`), which aren't names Oracle uses: the `shape` attribute is, and `ocpuPrice` and `memoryGbPrice` give any other size.
- **`ibm`**, IBM Cloud Virtual Server for VPC profiles (`bx3d-2x10`), per hour, by region. The only variant key is `capacityType`, `On-Demand`, `Spot` or `Burstable 50%`, `25%` or `10%`. `Pricing().Reserved` has reservations, with the term `1yr` or `3yr`, `Reserved`, `No Upfront`, and `hourly` the reservation's rate. About 90 older profiles (`bx2`, `cx2`, `mx2`, `gx2`, ...) have no public on-demand price of their own, so theirs is IBM's rate for an hourly reservation, which is an approximation.

All of their histories start in November 2026.

There is no single-instance fetch for Azure, Google Cloud, Hetzner, OVHcloud, Oracle Cloud or IBM Cloud yet; download their
bundles instead.

## One instance

`FetchAWSInstance(ctx, platform, instanceType, opts)` fetches a single instance from the
Infrawrench API instead of downloading the platform's whole bundle. It returns the same
`*AWSInstance` that `Get` does, or `nil` with no error if the platform has no instance with
that name:

```go
m5, err := bulkinstances.FetchAWSInstance(ctx, "ec2", "m5.large", bulkinstances.AWSInstanceOptions{})
if err != nil {
	return err
}
if m5 != nil {
	_ = len(m5.Pricing().OnDemand)
}
```

`AWSInstanceOptions` takes `Token` and `HTTPClient` like the bundle download, and `BaseURL` for
where the API is served from (`https://app.infrawrench.com` by default). Nothing is cached. The
API syncs each new bundle within about half an hour of it being published, so it can briefly
trail `DownloadAWSPricingData`.

`FetchRunpodInstance(ctx, id, opts)` and `FetchAlibabaInstance(ctx, instanceType, opts)` do the same for
RunPod and Alibaba Cloud, with the same `AWSInstanceOptions`, the same errors and the same half-hour sync.
They return a `*RunpodInstance` or `*AlibabaInstance` (or `nil`), which embed `*AWSInstance`. RunPod's ids have
spaces; pass them as they are, they are escaped for you.

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
