# com.infrawrench:bulk-instances

AWS EC2 instance attributes and prices, with their full history, from the bundle
Infrawrench publishes at `instances-bundles.infrawrench.com`.

```xml
<dependency>
  <groupId>com.infrawrench</groupId>
  <artifactId>bulk-instances</artifactId>
  <version>1.0.0</version>
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

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`cachePath`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Pass `cachePricingData(false)`
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
