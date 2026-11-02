# com.infrawrench:bulk-instances

AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full
history, from the bundles Infrawrench publishes at `instances-bundles.infrawrench.com`.

```xml
<dependency>
  <groupId>com.infrawrench</groupId>
  <artifactId>bulk-instances</artifactId>
  <version>1.4.0</version>
</dependency>
```

Requires Java 17 or later. The module name is `com.infrawrench.bulkinstances`.

```java
import com.infrawrench.bulkinstances.AWSInstance;
import com.infrawrench.bulkinstances.AWSPricingData;
import com.infrawrench.bulkinstances.AWSPricingDataOptions;
import com.infrawrench.bulkinstances.BulkInstances;
import com.infrawrench.bulkinstances.OnDemandPrice;
import java.util.Optional;

AWSPricingData data = BulkInstances.downloadAwsEc2PricingData(
        AWSPricingDataOptions.builder().token(System.getenv("INFRAWRENCH_API_KEY")).build());

data.keys(); // [m5.large, t2.micro, ...]

AWSInstance m5 = data.get("m5.large").orElseThrow();
m5.attributes().get("vcpu"); // "2"
m5.attributesIn("US East (N. Virginia)"); // with that region's overrides
m5.pricing().onDemand().stream()
        .filter(p -> p.location().regionCode().equals(Optional.of("us-east-1"))
                && p.variant().operatingSystem().equals("Linux") && p.variant().tenancy().equals("Shared")
                && p.variant().preInstalledSw().equals("NA") && p.variant().capacitystatus().equals("Used"))
        .findFirst()
        .map(OnDemandPrice::hourly); // Optional[0.096]

m5.attributesHistory(); // every attribute change, oldest first
m5.pricingHistory().reserved(); // every reserved price change, oldest first
```

Any Infrawrench bearer credential works as `token` (an `iwk_` API key, an agent
credential or a WorkOS access token). It defaults to `INFRAWRENCH_API_KEY`.

Failures to download throw `AWSPricingDataException`, an `IOException` whose
`status()` is the HTTP status when there was a response (401 for a rejected
token). Other `IOException`s mean the cache could not be read or written, or the
bundle is corrupt.

## Other AWS platforms

`BulkInstances.downloadAwsPricingData(platform, options)` loads any platform's bundle;
`downloadAwsEc2PricingData(options)` is the same as `downloadAwsPricingData("ec2", options)`.
`BulkInstances.AWS_PLATFORMS` lists the platforms; any other lowercase name is requested as is.

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

The fields that pick a price differ by platform. `data.variantKeys()` names them, and every
price's `variant().fields()` is a map keyed by them:

```java
AWSPricingData rds = BulkInstances.downloadAwsPricingData("rds");
rds.variantKeys(); // [databaseEngine, databaseEdition, licenseModel, deploymentOption, ...]
rds.get("db.m5.large").orElseThrow().pricing().onDemand().stream()
        .filter(p -> p.location().regionCode().equals(Optional.of("us-east-1"))
                && p.variant().fields().get("databaseEngine").equals("MySQL")
                && p.variant().fields().get("deploymentOption").equals("Multi-AZ"))
        .findFirst()
        .map(OnDemandPrice::hourly);
```

`operatingSystem()`, `tenancy()`, `licenseModel()`, `preInstalledSw()` and `capacitystatus()`
are EC2's variant fields. On other platforms they are `""`, unless the platform has a field
with that name (RDS has `licenseModel`).

`spot` is EC2's spot prices. They are in `pricing().onDemand()`, one per region and `operatingSystem()` (`Linux` or
`Windows`): the lowest price across the region's availability zones, as AWS's Spot pricing page shows it.
Its locations are region codes, so `location().region()` and `location().regionCode()` are both `us-east-1`. Spot instances
have no attributes; take their specs from `ec2`. The history goes back to August 2026, hourly at
first and every 6 hours since November 2026, and prices change far more often than on-demand prices.

## RunPod

`BulkInstances.downloadRunpodPricingData(options)` loads RunPod's GPU and CPU pod prices. It takes the same
options as the AWS methods (`RunpodPricingDataOptions`, a subclass of `AWSPricingDataOptions` built the same
way), caches the same way, and fails with a `RunpodPricingDataException`, a subclass of
`AWSPricingDataException`. It returns a `RunpodPricingData`, whose `get` returns an `Optional<RunpodInstance>`;
they have the same members as `AWSPricingData` and `AWSInstance`. `RunpodInstance` extends `AWSInstance`;
`RunpodPricingData` and `AWSPricingData` both extend `PricingData<I>`, where `I` is the instance class `get`
returns, so code that works with any bundle can take a `PricingData<?>`.

```java
RunpodPricingData runpod = BulkInstances.downloadRunpodPricingData();
runpod.get("NVIDIA H100 80GB HBM3").orElseThrow().pricing().onDemand().stream()
        .filter(p -> p.variant().fields().get("cloudType").equals("Secure Cloud"))
        .findFirst()
        .map(OnDemandPrice::hourly);
```

It has GPU types by RunPod's id (`NVIDIA H100 80GB HBM3`), priced per GPU per hour, and CPU pods by pod id
(`cpu3c-2-4`: flavor, vCPUs, GB of memory), priced per pod per hour; the `productFamily` attribute is `GPU` or
`CPU`. Prices are the same in every data center, so every price is in the location `global`. The only variant
key is `cloudType`, `Secure Cloud` or `Community Cloud`. Savings plans are in `pricing().reserved()` with the
term `3mo` or `6mo`, `Savings Plan`, `All Upfront`, and `hourly()` is the plan's effective hourly rate. Stock
levels and spot prices are not included. The history starts in November 2026.

`BulkInstances.fetchRunpodInstance(id, options)` fetches one GPU type or CPU pod from the Infrawrench API
instead (see [One instance](#one-instance)). It returns an `Optional<RunpodInstance>`, empty if RunPod has no
instance with that id, and fails with a `RunpodPricingDataException`:

```java
Optional<RunpodInstance> h100 = BulkInstances.fetchRunpodInstance("NVIDIA H100 80GB HBM3");
```

## Alibaba Cloud

`BulkInstances.downloadAlibabaPricingData(options)` loads Alibaba Cloud ECS prices. It takes the same options as
the AWS methods (`AlibabaPricingDataOptions`, a subclass of `AWSPricingDataOptions` built the same way), caches
the same way, and fails with an `AlibabaPricingDataException`, a subclass of `AWSPricingDataException`. It
returns an `AlibabaPricingData`, whose `get` returns an `Optional<AlibabaInstance>`; they have the same members
as `AWSPricingData` and `AWSInstance`, and are related to them as RunPod's are.

```java
AlibabaPricingData alibaba = BulkInstances.downloadAlibabaPricingData();
alibaba.get("ecs.g6.large").orElseThrow().pricing().onDemand().stream()
        .filter(p -> p.location().regionCode().equals(Optional.of("cn-hangzhou"))
                && p.variant().operatingSystem().equals("Linux")
                && p.variant().fields().get("networkType").equals("VPC"))
        .findFirst()
        .map(OnDemandPrice::hourly);
```

Its locations are region ids (`cn-hangzhou`), so the location and its region code are the same, and `regions()`
gives each an English `name`. Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `networkType`
(`VPC`, or `Classic` in older history). `pricing().onDemand()` has pay-as-you-go prices. `pricing().reserved()`
has subscriptions, with the term `1mo` or `1yr` to `5yr`, `Subscription`, `All Upfront`: they are paid in full
when bought, so `hourly()` is 0 and `upfront()` is the price. It also has reserved instances, with the term
`1yr` or `3yr`, `Reserved Instance`, and a purchase option. Attributes are Alibaba's instance type definitions
(`CpuCoreCount`, `MemorySize`, `CpuOptions.ThreadsPerCore`, ...), from May 2023 on. The history starts in
May 2018.

`BulkInstances.fetchAlibabaInstance(instanceType, options)` fetches one instance type from the Infrawrench API
instead (see [One instance](#one-instance)). It returns an `Optional<AlibabaInstance>`, empty if Alibaba has no
instance type with that name, and fails with an `AlibabaPricingDataException`:

```java
Optional<AlibabaInstance> g6 = BulkInstances.fetchAlibabaInstance("ecs.g6.large");
```

## One instance

`BulkInstances.fetchAwsInstance(platform, instanceType, options)` fetches a single instance from
the Infrawrench API instead of downloading the platform's whole bundle. It returns the same
`AWSInstance` that `get` does, or empty if the platform has no instance with that name:

```java
Optional<AWSInstance> m5 = BulkInstances.fetchAwsInstance("ec2", "m5.large");
m5.map(i -> i.pricing().onDemand().size());
```

Its options are an `AWSInstanceOptions`, built like `AWSPricingDataOptions`: `token`, and `baseUrl`
for where the API is served from (`https://app.infrawrench.com` by default). Nothing is cached. The
API syncs each new bundle within about half an hour of it being published, so it can briefly trail
`downloadAwsPricingData`.

`BulkInstances.fetchRunpodInstance(id, options)` and `BulkInstances.fetchAlibabaInstance(instanceType, options)`
do the same for RunPod and Alibaba Cloud, with the same half-hour sync. Their options are a
`RunpodInstanceOptions` or `AlibabaInstanceOptions`, subclasses of `AWSInstanceOptions` built the same way. They
return an `Optional<RunpodInstance>` or `Optional<AlibabaInstance>` and fail with the provider's exception.
RunPod's ids have spaces; pass them as they are, they are escaped for you.

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`cachePath`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Each platform's bundle is cached
under its own name (`rds-bundle-…json`), so loading one never evicts another. Pass `cachePricingData(false)`
to always download and never touch the disk. The cache is shared with the other
Infrawrench SDKs.

Loading decompresses and parses the whole bundle into compact raw rows.
Instances are decoded lazily: `get` only wraps the raw rows, and `attributes()`,
`attributesHistory()`, `pricing()` and `pricingHistory()` each decode on first
access and keep the result. The returned objects are immutable records and
unmodifiable collections, shared between calls and safe to use from several
threads.

## Prices and regions

- `location().region()` is the AWS location name (`US East (N. Virginia)`),
  `location().regionCode()` its code (`us-east-1`) where the price list gives
  one, and empty otherwise.
- `pricing()` holds only what is still offered. In `pricingHistory()`, an empty
  `hourly()` means the price stopped being offered at `at()`.
- Instances AWS no longer lists are still in `keys()`, with `deletedAt()` set and
  empty `pricing()`.
