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
| `spot` | EC2 Spot (see below) |

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

`spot` is EC2's spot prices. They are in `pricing.onDemand`, one per region and `operatingSystem` (`Linux` or
`Windows`): the lowest price across the region's availability zones, as AWS's Spot pricing page shows it.
Its locations are region codes, so `region` and `regionCode` are both `us-east-1`. Spot instances
have no attributes; take their specs from `ec2`. The history goes back to August 2026, hourly at
first and every 6 hours since November 2026, and prices change far more often than on-demand prices.

## RunPod

`downloadRunpodPricingData(options)` loads RunPod's GPU and CPU pod prices. It takes the same options as the
AWS functions (`RunpodPricingDataOptions`), caches the same way, and fails with a `RunpodPricingDataError`, a
subclass of `AWSPricingDataError`. It returns a `RunpodPricingData`, whose `get` returns a `RunpodInstance`;
they have the same members as `AWSPricingData` and `AWSInstance`.

```ts
import { downloadRunpodPricingData } from "@infrawrench/bulk-instances";

const runpod = await downloadRunpodPricingData();
runpod.get("NVIDIA H100 80GB HBM3")?.pricing.onDemand.find((p) => p.variant.cloudType === "Secure Cloud")?.hourly;
```

It has GPU types by RunPod's id (`NVIDIA H100 80GB HBM3`), priced per GPU per hour, and CPU pods by pod id
(`cpu3c-2-4`: flavor, vCPUs, GB of memory), priced per pod per hour; the `productFamily` attribute is `GPU` or
`CPU`. Prices are the same in every data center, so every price is in the location `global`. The only variant
key is `cloudType`, `Secure Cloud` or `Community Cloud`. Savings plans are in `pricing.reserved` with the term
`3mo` or `6mo`, `Savings Plan`, `All Upfront`, and `hourly` is the plan's effective hourly rate. Stock levels
and spot prices are not included. The history starts in November 2026.

`fetchRunpodInstance(id, options)` fetches one GPU type or CPU pod from the Infrawrench API instead (see
[One instance](#one-instance)). It returns a `RunpodInstance`, or `undefined` if RunPod has no instance with
that id, and fails with a `RunpodPricingDataError`:

```ts
import { fetchRunpodInstance } from "@infrawrench/bulk-instances";

const h100 = await fetchRunpodInstance("NVIDIA H100 80GB HBM3");
```

## Alibaba Cloud

`downloadAlibabaPricingData(options)` loads Alibaba Cloud ECS prices. It takes the same options as the AWS
functions (`AlibabaPricingDataOptions`), caches the same way, and fails with an `AlibabaPricingDataError`, a
subclass of `AWSPricingDataError`. It returns an `AlibabaPricingData`, whose `get` returns an
`AlibabaInstance`; they have the same members as `AWSPricingData` and `AWSInstance`.

```ts
import { downloadAlibabaPricingData } from "@infrawrench/bulk-instances";

const alibaba = await downloadAlibabaPricingData();
alibaba.get("ecs.g6.large")?.pricing.onDemand.find(
  (p) => p.regionCode === "cn-hangzhou" && p.variant.operatingSystem === "Linux" && p.variant.networkType === "VPC",
)?.hourly;
```

Its locations are region ids (`cn-hangzhou`), so the location and its region code are the same, and `regions`
gives each an English `name`. Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `networkType`
(`VPC`, or `Classic` in older history). `pricing.onDemand` has pay-as-you-go prices. `pricing.reserved` has
subscriptions, with the term `1mo` or `1yr` to `5yr`, `Subscription`, `All Upfront`: they are paid in full
when bought, so `hourly` is 0 and `upfront` is the price. It also has reserved instances, with the term `1yr` or
`3yr`, `Reserved Instance`, and a purchase option. Attributes are Alibaba's instance type definitions
(`CpuCoreCount`, `MemorySize`, `CpuOptions.ThreadsPerCore`, ...), from May 2023 on. The history starts in
May 2018.

`fetchAlibabaInstance(instanceType, options)` fetches one instance type from the Infrawrench API instead (see
[One instance](#one-instance)). It returns an `AlibabaInstance`, or `undefined` if Alibaba has no instance type
with that name, and fails with an `AlibabaPricingDataError`:

```ts
import { fetchAlibabaInstance } from "@infrawrench/bulk-instances";

const g6 = await fetchAlibabaInstance("ecs.g6.large");
```

## Azure

`downloadAzurePricingData(options)` loads Azure virtual machine prices. It takes the same options as the AWS
functions (`AzurePricingDataOptions`), caches the same way, and fails with an `AzurePricingDataError`, a
subclass of `AWSPricingDataError`. It returns an `AzurePricingData`, whose `get` returns an
`AzureInstance`; they have the same members as `AWSPricingData` and `AWSInstance`.

```ts
import { downloadAzurePricingData } from "@infrawrench/bulk-instances";

const azure = await downloadAzurePricingData();
azure.get("Standard_D2s_v3")?.pricing.onDemand.find(
  (p) => p.regionCode === "eastus" && p.variant.operatingSystem === "Linux" && p.variant.priority === "Regular",
)?.hourly;
```

It has VM sizes by ARM name (`Standard_D2s_v3`), priced per VM per hour. Its locations are ARM region names
(`eastus`), so the location and its region code are the same, and `regions` gives each Azure's display `name`
(`US East`). Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `priority` (`Regular`, `Spot`
or `Low Priority`). `pricing.onDemand` has pay-as-you-go prices, dated by when Azure says they took effect.
`pricing.reserved` has reservations, with the term `1yr`, `3yr` or `5yr`, `Reserved Instance`, `All Upfront`:
`hourly` is 0 and `upfront` is the whole term's price. Azure lists reservations under `Linux` only; on Windows
the license is billed on top. It also has savings plans, with the term `1yr` or `3yr`, `Savings Plan`,
`No Upfront`, and `hourly` is the plan's rate. Attributes are `skuName`, `productName` and, from Azure's
pricing calculator, `cores`, `ram` (GB), `diskSize` (temporary disk, GB), `gpu` and `series`. About a third of
sizes, mostly the newest and retired series, have no calculator specs. Dedicated hosts are not included. The
history starts in November 2026.

## Google Cloud

`downloadGcpPricingData(options)` loads Google Cloud Compute Engine prices. It takes the same options as the AWS
functions (`GCPPricingDataOptions`), caches the same way, and fails with a `GCPPricingDataError`, a
subclass of `AWSPricingDataError`. It returns a `GCPPricingData`, whose `get` returns a
`GCPInstance`; they have the same members as `AWSPricingData` and `AWSInstance`.

```ts
import { downloadGcpPricingData } from "@infrawrench/bulk-instances";

const gcp = await downloadGcpPricingData();
gcp.get("n2-standard-2")?.pricing.onDemand.find(
  (p) => p.regionCode === "us-central1" && p.variant.provisioningModel === "Standard",
)?.hourly;
```

It has machine types by name (`n2-standard-2`), priced per VM per hour. Google bills most machine types per
vCPU and per GiB of memory at their family's rates, plus their GPUs, so each price is worked out from those
rates and the machine type's shape. Prices leave out bundled Local SSD, OS licenses and sustained use
discounts, and TPU, X4, X5 and A4X machine types aren't included. Its locations are regions (`us-central1`),
so the location and its region code are the same. The only variant key is `provisioningModel`, `Standard` or
`Spot`. `pricing.reserved` has committed use discounts, with the term `1yr` or `3yr`, `Committed Use`,
`No Upfront`, and `hourly` is the commitment's rate. Attributes are the machine type's fields from the Compute
Engine API (`guestCpus`, `memoryMb`, `description`, `isSharedCpu`, ...), `acceleratorType` and
`acceleratorCount` for its GPUs, and `zones`, the zones in each region that have it, which differ by region
(see `attributesIn(region)`). The history starts in November 2026.

## Hetzner, OVHcloud, Oracle Cloud and IBM Cloud

These load the same way as Google Cloud's, with the same options, caching and failures. Each returns its own data and
instance types, which have the same members as the AWS ones.

| Function | Data | Instance | Error |
| --- | --- | --- | --- |
| `downloadHetznerPricingData` | `HetznerPricingData` | `HetznerInstance` | `HetznerPricingDataError` |
| `downloadHetznerAuctionPricingData` | `HetznerAuctionPricingData` | `HetznerAuctionInstance` | `HetznerAuctionPricingDataError` |
| `downloadOvhPricingData` | `OVHPricingData` | `OVHInstance` | `OVHPricingDataError` |
| `downloadOvhEcoPricingData` | `OVHEcoPricingData` | `OVHEcoInstance` | `OVHEcoPricingDataError` |
| `downloadOraclePricingData` | `OraclePricingData` | `OracleInstance` | `OraclePricingDataError` |
| `downloadIbmPricingData` | `IBMPricingData` | `IBMInstance` | `IBMPricingDataError` |

```ts
import { downloadHetznerPricingData } from "@infrawrench/bulk-instances";

const hetzner = await downloadHetznerPricingData();
hetzner.get("cx23")?.pricing.onDemand.find(
  (p) => p.regionCode === "fsn1" && p.variant.ipv4 === "Primary IPv4",
)?.hourly;
```

- **`hetzner`**, Hetzner cloud servers, by Cloud API name (`cx23`), per hour. Locations are Cloud API location names (`fsn1`, `ash`). The only variant key is `ipv4`, `IPv6 only` or `Primary IPv4`, since a primary IPv4 is optional and billed apart. `pricing.reserved` has the monthly cap, with the term `1mo`, `Monthly Cap`, `Postpaid`, `hourly` 0 and `upfront` the cap. Attributes include `cores`, `cpu`, `memoryInGb`, `diskInGb` and `architecture`.
- **`hetznerauction`**, Hetzner Server Auction listings, by listing id (`3107671`). Each is one physical server, so its history runs from when it is listed until it is sold, and it has the same variant key and term as `hetzner`. Attributes are the listing's hardware and details (`CPU.Name`, `RAM.Size`, `datacenter`, `fixedPrice`, `setupFee`, ...). The bundle is read hourly, so a price drop is dated by the read that saw it.
- **`ovh`**, OVHcloud Public Cloud flavors (`b3-8`), per hour, from the World and US catalogs, in USD. Locations are pricing zones, not regions: `world`, `3az`, `lz-eu`, `lz-eurozone`, `lz-af`, `us` and `us-east-lz-dal-a`. The only variant key is `operatingSystem`. `pricing.reserved` has monthly plans where a flavor has them, with the term `1mo`, `Monthly`, `Postpaid` or `All Upfront`, `hourly` 0 and `upfront` the month's price.
- **`ovheco`**, OVHcloud's Kimsufi, So you Start, Rise and Advance servers (`24sys01`), by data center (`gra`, `sgp`); the `range` attribute says which. **These have no on-demand prices**, because they are only rented by the month. The rent is in `pricing.reserved`, with the term `1mo`, `Rental`, `All Upfront`, `hourly` 0 and `upfront` the rent, beside prepaying (`1yr` or `2yr`, `Prepaid`). The variant keys are `memory`, `storage` and `systemStorage`, which is often empty.
- **`oracle`**, Oracle Cloud VM and bare metal shapes, per hour, the same in every commercial region, so every price is in `global`. The only variant key is `operatingSystem`. Flexible shapes have no one price, so they are priced at a set of sizes named `<shape>-<ocpus>-<GB>` (`VM.Standard.E5.Flex-2-16`), which aren't names Oracle uses: the `shape` attribute is, and `ocpuPrice` and `memoryGbPrice` give any other size.
- **`ibm`**, IBM Cloud Virtual Server for VPC profiles (`bx3d-2x10`), per hour, by region. The only variant key is `capacityType`, `On-Demand`, `Spot` or `Burstable 50%`, `25%` or `10%`. `pricing.reserved` has reservations, with the term `1yr` or `3yr`, `Reserved`, `No Upfront`, and `hourly` the reservation's rate. About 90 older profiles (`bx2`, `cx2`, `mx2`, `gx2`, ...) have no public on-demand price of their own, so theirs is IBM's rate for an hourly reservation, which is an approximation.

All of their histories start in November 2026.

There is no single-instance fetch for Azure, Google Cloud, Hetzner, OVHcloud, Oracle Cloud or IBM Cloud yet; download their
bundles instead.

## One instance

`fetchAwsInstance(platform, instanceType, options)` fetches a single instance from the Infrawrench
API instead of downloading the platform's whole bundle. It returns the same `AWSInstance` that
`get` does, or `undefined` if the platform has no instance with that name:

```ts
import { fetchAwsInstance } from "@infrawrench/bulk-instances";

const m5 = await fetchAwsInstance("ec2", "m5.large");
m5?.pricing.onDemand.length;
```

It takes `token` like the bundle download, and `baseUrl` for where the API is served from
(`https://app.infrawrench.com` by default). Nothing is cached. The API syncs each new bundle within
about half an hour of it being published, so it can briefly trail `downloadAwsPricingData`.

`fetchRunpodInstance(id, options)` and `fetchAlibabaInstance(instanceType, options)` do the same for RunPod
and Alibaba Cloud, with the same options (`RunpodInstanceOptions`, `AlibabaInstanceOptions`) and the same
half-hour sync. They return a `RunpodInstance` or `AlibabaInstance` (or `undefined`) and fail with the
provider's error. RunPod's ids have spaces; pass them as they are, they are escaped for you.

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
