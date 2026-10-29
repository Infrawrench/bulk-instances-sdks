# Infrawrench.BulkInstances

AWS EC2 instance attributes and prices, with their full history, from the bundle
Infrawrench publishes at `instances-bundles.infrawrench.com`.

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

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`CachePath`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Set `CachePricingData = false`
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
