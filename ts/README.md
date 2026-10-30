# @infrawrench/bulk-instances

AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full
history, from the bundles Infrawrench publishes at `instances-bundles.infrawrench.com`.

```ts
import { downloadAwsEc2PricingData } from "@infrawrench/bulk-instances";

const data = await downloadAwsEc2PricingData({ token: process.env.INFRAWRENCH_API_KEY });

data.keys(); // ["m5.large", "t2.micro", ...]

const m5 = data.get("m5.large")!;
m5.attributes.vcpu; // "2"
m5.attributesIn("US East (N. Virginia)"); // with that region's overrides
m5.pricing.onDemand.find(
  (p) => p.regionCode === "us-east-1" && p.operatingSystem === "Linux" && p.tenancy === "Shared" &&
    p.preInstalledSw === "NA" && p.capacitystatus === "Used",
)?.hourly; // 0.096

m5.attributesHistory; // every attribute change, oldest first
m5.pricingHistory.reserved; // every reserved price change, oldest first
```

Any Infrawrench bearer credential works as `token` (an `iwk_` API key, an agent
credential or a WorkOS access token). It defaults to `INFRAWRENCH_API_KEY`.

## Other AWS platforms

`downloadAwsPricingData(platform, options)` loads any platform's bundle;
`downloadAwsEc2PricingData(options)` is the same as `downloadAwsPricingData("ec2", options)`.

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

The fields that pick a price differ by platform. `data.variantKeys` names them, and every
price has a `variant` object keyed by them:

```ts
import { downloadAwsPricingData } from "@infrawrench/bulk-instances";

const rds = await downloadAwsPricingData("rds");
rds.variantKeys; // ["databaseEngine", "databaseEdition", "licenseModel", "deploymentOption", ...]
rds.get("db.m5.large")!.pricing.onDemand.find(
  (p) => p.regionCode === "us-east-1" && p.variant.databaseEngine === "MySQL" &&
    p.variant.deploymentOption === "Multi-AZ",
)?.hourly;
```

`operatingSystem`, `tenancy`, `licenseModel`, `preInstalledSw` and `capacitystatus` are EC2's
variant fields. On other platforms they are `""`, unless the platform has a field with that name
(RDS has `licenseModel`).

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`cachePath`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Each platform's bundle is cached
under its own name (`rds-bundle-…json`), so loading one never evicts another. Pass `cachePricingData: false`
to always download and never touch the disk.

Loading decompresses and parses the whole bundle. Instances are decoded lazily:
`get` only wraps the raw rows, and `attributes`, `attributesHistory`, `pricing`
and `pricingHistory` each decode on first access and keep the result. The
returned objects are shared between calls, so treat them as read-only.

## Prices and regions

- `region` is the AWS location name (`US East (N. Virginia)`), `regionCode` its
  code (`us-east-1`) where the price list gives one.
- `pricing` holds only what is still offered. In `pricingHistory`, a `null`
  `hourly` means the price stopped being offered at `at`.
- Instances AWS no longer lists are still in `keys()`, with `deletedAt` set and
  empty `pricing`.
