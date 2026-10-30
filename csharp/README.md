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
