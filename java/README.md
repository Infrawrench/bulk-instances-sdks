# com.infrawrench:bulk-instances

AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full
history, from the bundles Infrawrench publishes at `instances-bundles.infrawrench.com`.

```xml
<dependency>
  <groupId>com.infrawrench</groupId>
  <artifactId>bulk-instances</artifactId>
  <version>1.2.0</version>
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
