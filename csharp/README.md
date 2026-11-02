# Infrawrench.BulkInstances

AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full
history, from the bundles Infrawrench publishes at `instances-bundles.infrawrench.com`.

```sh
dotnet add package Infrawrench.BulkInstances
```

```csharp
using Infrawrench.BulkInstances;

var data = await BulkInstances.DownloadAwsEc2PricingDataAsync(new AwsPricingDataOptions
{
    Token = Environment.GetEnvironmentVariable("INFRAWRENCH_API_KEY"),
});

var keys = data.Keys; // ["m5.large", "t2.micro", ...]

var m5 = data.Get("m5.large")!;
var vcpu = m5.Attributes["vcpu"]; // "2"
var inUsEast = m5.AttributesIn("US East (N. Virginia)"); // with that region's overrides
var hourly = m5.Pricing.OnDemand.FirstOrDefault(
    p => p.RegionCode == "us-east-1" && p.OperatingSystem == "Linux" && p.Tenancy == "Shared" &&
        p.PreInstalledSw == "NA" && p.Capacitystatus == "Used")?.Hourly; // 0.096

var attributeChanges = m5.AttributesHistory; // every attribute change, oldest first
var reservedChanges = m5.PricingHistory.Reserved; // every reserved price change, oldest first
```

Any Infrawrench bearer credential works as `Token` (an `iwk_` API key, an agent
credential or a WorkOS access token). It defaults to `INFRAWRENCH_API_KEY`.
Failures to download throw `AwsPricingDataException`, whose `Status` is the HTTP
status if there was a response.

## Other AWS platforms

`BulkInstances.DownloadAwsPricingDataAsync(platform, options)` loads any platform's bundle;
`DownloadAwsEc2PricingDataAsync(options)` is the same as `DownloadAwsPricingDataAsync("ec2", options)`.
`BulkInstances.AwsPlatforms` lists the platforms:

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

The fields that pick a price differ by platform. `data.VariantKeys` names them, and every
price has a `Variant` dictionary keyed by them, in that order:

```csharp
var rds = await BulkInstances.DownloadAwsPricingDataAsync("rds");
var variantKeys = rds.VariantKeys; // ["databaseEngine", "databaseEdition", "licenseModel", "deploymentOption", ...]
var multiAz = rds.Get("db.m5.large")!.Pricing.OnDemand.FirstOrDefault(
    p => p.RegionCode == "us-east-1" && p.Variant["databaseEngine"] == "MySQL" &&
        p.Variant["deploymentOption"] == "Multi-AZ")?.Hourly;
```

`OperatingSystem`, `Tenancy`, `LicenseModel`, `PreInstalledSw` and `Capacitystatus` are EC2's
variant fields. On other platforms they are `""`, unless the platform has a field with that name
(RDS has `licenseModel`).

`spot` is EC2's spot prices. They are in `Pricing.OnDemand`, one per region and `OperatingSystem` (`Linux` or
`Windows`): the lowest price across the region's availability zones, as AWS's Spot pricing page shows it.
Its locations are region codes, so `Region` and `RegionCode` are both `us-east-1`. Spot instances
have no attributes; take their specs from `ec2`. The history goes back to August 2026, hourly at
first and every 6 hours since November 2026, and prices change far more often than on-demand prices.

## RunPod

`BulkInstances.DownloadRunpodPricingDataAsync(options)` loads RunPod's GPU and CPU pod prices. It takes the same
options as the AWS methods (`RunpodPricingDataOptions`, a subclass of `AwsPricingDataOptions`), caches the same
way, and fails with a `RunpodPricingDataException`, a subclass of `AwsPricingDataException`. It returns a
`RunpodPricingData`, whose `Get` and `TryGet` give a `RunpodInstance`; they are subclasses of `AwsPricingData`
and `AwsInstance`, with the same members.

```csharp
var runpod = await BulkInstances.DownloadRunpodPricingDataAsync();
var secure = runpod.Get("NVIDIA H100 80GB HBM3")?.Pricing.OnDemand.FirstOrDefault(
    p => p.Variant["cloudType"] == "Secure Cloud")?.Hourly;
```

It has GPU types by RunPod's id (`NVIDIA H100 80GB HBM3`), priced per GPU per hour, and CPU pods by pod id
(`cpu3c-2-4`: flavor, vCPUs, GB of memory), priced per pod per hour; the `productFamily` attribute is `GPU` or
`CPU`. Prices are the same in every data center, so every price is in the location `global`. The only variant
key is `cloudType`, `Secure Cloud` or `Community Cloud`. Savings plans are in `Pricing.Reserved` with the term
`3mo` or `6mo`, `Savings Plan`, `All Upfront`, and `Hourly` is the plan's effective hourly rate. Stock levels
and spot prices are not included. The history starts in November 2026.

`BulkInstances.FetchRunpodInstanceAsync(id, options, cancellationToken)` fetches one GPU type or CPU pod from the
Infrawrench API instead (see [One instance](#one-instance)). It returns a `RunpodInstance`, or `null` if RunPod
has no instance with that id, and fails with a `RunpodPricingDataException`:

```csharp
var h100 = await BulkInstances.FetchRunpodInstanceAsync("NVIDIA H100 80GB HBM3");
```

## Alibaba Cloud

`BulkInstances.DownloadAlibabaPricingDataAsync(options)` loads Alibaba Cloud ECS prices. It takes the same
options as the AWS methods (`AlibabaPricingDataOptions`, a subclass of `AwsPricingDataOptions`), caches the same
way, and fails with an `AlibabaPricingDataException`, a subclass of `AwsPricingDataException`. It returns an
`AlibabaPricingData`, whose `Get` and `TryGet` give an `AlibabaInstance`; they are subclasses of
`AwsPricingData` and `AwsInstance`, with the same members.

```csharp
var alibaba = await BulkInstances.DownloadAlibabaPricingDataAsync();
var hangzhou = alibaba.Get("ecs.g6.large")?.Pricing.OnDemand.FirstOrDefault(
    p => p.RegionCode == "cn-hangzhou" && p.OperatingSystem == "Linux" && p.Variant["networkType"] == "VPC")?.Hourly;
```

Its locations are region ids (`cn-hangzhou`), so `Region` and `RegionCode` are the same, and `Regions` gives
each an English `name`. Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `networkType` (`VPC`,
or `Classic` in older history). `Pricing.OnDemand` has pay-as-you-go prices. `Pricing.Reserved` has
subscriptions, with the term `1mo` or `1yr` to `5yr`, `Subscription`, `All Upfront`: they are paid in full when
bought, so `Hourly` is 0 and `Upfront` is the price. It also has reserved instances, with the term `1yr` or
`3yr`, `Reserved Instance`, and a purchase option. Attributes are Alibaba's instance type definitions
(`CpuCoreCount`, `MemorySize`, `CpuOptions.ThreadsPerCore`, ...), from May 2023 on. The history starts in
May 2018.

`BulkInstances.FetchAlibabaInstanceAsync(instanceType, options, cancellationToken)` fetches one instance type
from the Infrawrench API instead (see [One instance](#one-instance)). It returns an `AlibabaInstance`, or `null`
if Alibaba has no instance type with that name, and fails with an `AlibabaPricingDataException`:

```csharp
var g6 = await BulkInstances.FetchAlibabaInstanceAsync("ecs.g6.large");
```

## One instance

`BulkInstances.FetchAwsInstanceAsync(platform, instanceType, options, cancellationToken)` fetches a
single instance from the Infrawrench API instead of downloading the platform's whole bundle. It
returns the same `AwsInstance` that `Get` does, or `null` if the platform has no instance with that
name:

```csharp
var m5 = await BulkInstances.FetchAwsInstanceAsync("ec2", "m5.large");
var count = m5?.Pricing.OnDemand.Count;
```

Its options are an `AwsInstanceOptions`: `Token`, and `BaseUrl` for where the API is served from
(`https://app.infrawrench.com` by default). Nothing is cached. The API syncs each new bundle within
about half an hour of it being published, so it can briefly trail `DownloadAwsPricingDataAsync`.

`BulkInstances.FetchRunpodInstanceAsync(id, ...)` and `BulkInstances.FetchAlibabaInstanceAsync(instanceType, ...)`
do the same for RunPod and Alibaba Cloud, with the same half-hour sync. Their options are a
`RunpodInstanceOptions` or `AlibabaInstanceOptions`, subclasses of `AwsInstanceOptions`. They return a
`RunpodInstance` or `AlibabaInstance` (or `null`) and fail with the provider's exception. RunPod's ids have
spaces; pass them as they are, they are escaped for you.

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`CachePath`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Each platform's bundle is cached
under its own name (`rds-bundle-…json`), so loading one never evicts another. Set `CachePricingData = false`
to always download and never touch the disk. The cache is shared with the other
Infrawrench bulk-instances SDKs.

Loading decompresses and scans the whole bundle. Instances are decoded lazily:
`Get` only wraps the raw rows, and `Attributes`, `AttributesHistory`, `Pricing`
and `PricingHistory` each decode on first access and keep the result. The
returned objects are shared between calls and read-only. Lazy decoding is not
locked: reading from several threads is safe, but a part first accessed
concurrently may be decoded more than once.

## Prices and regions

- `Region` is the AWS location name (`US East (N. Virginia)`), `RegionCode` its
  code (`us-east-1`) where the price list gives one, else `null`.
- `Pricing` holds only what is still offered. In `PricingHistory`, a `null`
  `Hourly` means the price stopped being offered at `At`.
- Instances AWS no longer lists are still in `Keys`, with `DeletedAt` set and
  empty `Pricing`.
