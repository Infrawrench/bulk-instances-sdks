# infrawrench-bulk-instances

AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full
history, from the bundles Infrawrench publishes at `instances-bundles.infrawrench.com`.

```sh
pip install infrawrench-bulk-instances
```

```python
import os

from infrawrench_bulk_instances import download_aws_ec2_pricing_data

data = download_aws_ec2_pricing_data(token=os.environ.get("INFRAWRENCH_API_KEY"))

data.keys()  # ["m5.large", "t2.micro", ...]

m5 = data.get("m5.large")
assert m5 is not None
m5.attributes["vcpu"]  # "2"
m5.attributes_in("US East (N. Virginia)")  # with that region's overrides
next(
    p.hourly
    for p in m5.pricing.on_demand
    if p.region_code == "us-east-1" and p.operating_system == "Linux" and p.tenancy == "Shared"
    and p.pre_installed_sw == "NA" and p.capacitystatus == "Used"
)  # 0.096

m5.attributes_history  # every attribute change, oldest first
m5.pricing_history.reserved  # every reserved price change, oldest first
```

Any Infrawrench bearer credential works as `token` (an `iwk_` API key, an agent
credential or a WorkOS access token). It defaults to `INFRAWRENCH_API_KEY`.
Failures raise `AWSPricingDataError`, whose `status` is the HTTP status, if there
was a response. Requires Python 3.10 or later; no dependencies.

## Other AWS platforms

`download_aws_pricing_data(platform, ...)` loads any platform's bundle;
`download_aws_ec2_pricing_data(...)` is the same as `download_aws_pricing_data("ec2", ...)`.
`AWS_PLATFORMS` lists them:

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

The fields that pick a price differ by platform. `data.variant_keys` names them, and every
price has a `variant` mapping keyed by them:

```python
from infrawrench_bulk_instances import download_aws_pricing_data

rds = download_aws_pricing_data("rds")
rds.variant_keys  # ("databaseEngine", "databaseEdition", "licenseModel", "deploymentOption", ...)
db = rds.get("db.m5.large")
assert db is not None
next(
    p.hourly
    for p in db.pricing.on_demand
    if p.region_code == "us-east-1" and p.variant["databaseEngine"] == "MySQL"
    and p.variant["deploymentOption"] == "Multi-AZ"
)
```

`operating_system`, `tenancy`, `license_model`, `pre_installed_sw` and `capacitystatus` are EC2's
variant fields. On other platforms they are `""`, unless the platform has a field with that name
(RDS has `licenseModel`).

`spot` is EC2's spot prices. They are in `pricing.on_demand`, one per region and `operating_system` (`Linux` or
`Windows`): the lowest price across the region's availability zones, as AWS's Spot pricing page shows it.
Its locations are region codes, so `region` and `region_code` are both `us-east-1`. Spot instances
have no attributes; take their specs from `ec2`. The history goes back to August 2026, hourly at
first and every 6 hours since November 2026, and prices change far more often than on-demand prices.

## RunPod

`download_runpod_pricing_data(...)` loads RunPod's GPU and CPU pod prices. It takes the same keyword
arguments as the AWS functions, caches the same way, and raises `RunpodPricingDataError`, a subclass of
`AWSPricingDataError`. It returns a `RunpodPricingData`, whose `get` returns a `RunpodInstance`; they have
the same members as `AWSPricingData` and `AWSInstance`.

```python
from infrawrench_bulk_instances import download_runpod_pricing_data

runpod = download_runpod_pricing_data()
h100 = runpod.get("NVIDIA H100 80GB HBM3")
assert h100 is not None
next(p.hourly for p in h100.pricing.on_demand if p.variant["cloudType"] == "Secure Cloud")
```

It has GPU types by RunPod's id (`NVIDIA H100 80GB HBM3`), priced per GPU per hour, and CPU pods by pod id
(`cpu3c-2-4`: flavor, vCPUs, GB of memory), priced per pod per hour; the `productFamily` attribute is `GPU` or
`CPU`. Prices are the same in every data center, so every price is in the location `global`. The only variant
key is `cloudType`, `Secure Cloud` or `Community Cloud`. Savings plans are in `pricing.reserved` with the term
`3mo` or `6mo`, `Savings Plan`, `All Upfront`, and `hourly` is the plan's effective hourly rate. Stock levels
and spot prices are not included. The history starts in November 2026.

## Alibaba Cloud

`download_alibaba_pricing_data(...)` loads Alibaba Cloud ECS prices. It takes the same keyword arguments as
the AWS functions, caches the same way, and raises `AlibabaPricingDataError`, a subclass of
`AWSPricingDataError`. It returns an `AlibabaPricingData`, whose `get` returns an `AlibabaInstance`; they
have the same members as `AWSPricingData` and `AWSInstance`.

```python
from infrawrench_bulk_instances import download_alibaba_pricing_data

alibaba = download_alibaba_pricing_data()
g6 = alibaba.get("ecs.g6.large")
assert g6 is not None
next(
    p.hourly
    for p in g6.pricing.on_demand
    if p.region_code == "cn-hangzhou" and p.variant["operatingSystem"] == "Linux"
    and p.variant["networkType"] == "VPC"
)
```

Its locations are region ids (`cn-hangzhou`), so the location and its region code are the same, and `regions`
gives each an English `name`. Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `networkType`
(`VPC`, or `Classic` in older history). `pricing.on_demand` has pay-as-you-go prices. `pricing.reserved` has
subscriptions, with the term `1mo` or `1yr` to `5yr`, `Subscription`, `All Upfront`: they are paid in full
when bought, so `hourly` is 0 and `upfront` is the price. It also has reserved instances, with the term `1yr` or
`3yr`, `Reserved Instance`, and a purchase option. Attributes are Alibaba's instance type definitions
(`CpuCoreCount`, `MemorySize`, `CpuOptions.ThreadsPerCore`, ...), from May 2023 on. The history starts in
May 2018.

## Azure

`download_azure_pricing_data(...)` loads Azure virtual machine prices. It takes the same keyword arguments as
the AWS functions, caches the same way, and raises `AzurePricingDataError`, a subclass of
`AWSPricingDataError`. It returns an `AzurePricingData`, whose `get` returns an `AzureInstance`; they
have the same members as `AWSPricingData` and `AWSInstance`.

```python
from infrawrench_bulk_instances import download_azure_pricing_data

azure = download_azure_pricing_data()
d2 = azure.get("Standard_D2s_v3")
assert d2 is not None
next(
    p.hourly
    for p in d2.pricing.on_demand
    if p.region_code == "eastus" and p.variant["operatingSystem"] == "Linux" and p.variant["priority"] == "Regular"
)
```

It has VM sizes by ARM name (`Standard_D2s_v3`), priced per VM per hour. Its locations are ARM region names
(`eastus`), so the location and its region code are the same, and `regions` gives each Azure's display `name`
(`US East`). Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `priority` (`Regular`, `Spot`
or `Low Priority`). `pricing.on_demand` has pay-as-you-go prices, dated by when Azure says they took effect.
`pricing.reserved` has reservations, with the term `1yr`, `3yr` or `5yr`, `Reserved Instance`, `All Upfront`:
`hourly` is 0 and `upfront` is the whole term's price. Azure lists reservations under `Linux` only; on Windows
the license is billed on top. It also has savings plans, with the term `1yr` or `3yr`, `Savings Plan`,
`No Upfront`, and `hourly` is the plan's rate. Attributes are `skuName`, `productName` and, from Azure's
pricing calculator, `cores`, `ram` (GB), `diskSize` (temporary disk, GB), `gpu` and `series`. About a third of
sizes, mostly the newest and retired series, have no calculator specs. Dedicated hosts are not included. The
history starts in November 2026.

## Google Cloud

`download_gcp_pricing_data(...)` loads Google Cloud Compute Engine prices. It takes the same keyword arguments as
the AWS functions, caches the same way, and raises `GCPPricingDataError`, a subclass of
`AWSPricingDataError`. It returns a `GCPPricingData`, whose `get` returns a `GCPInstance`; they
have the same members as `AWSPricingData` and `AWSInstance`.

```python
from infrawrench_bulk_instances import download_gcp_pricing_data

gcp = download_gcp_pricing_data()
n2 = gcp.get("n2-standard-2")
assert n2 is not None
next(
    p.hourly
    for p in n2.pricing.on_demand
    if p.region_code == "us-central1" and p.variant["provisioningModel"] == "Standard"
)
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
(see `attributes_in(region)`). The history starts in November 2026.

`fetch_aws_instance` doesn't cover RunPod, Alibaba, Azure or Google Cloud; download their bundles instead.

## One instance

`fetch_aws_instance(platform, instance_type, ...)` fetches a single instance from the Infrawrench
API instead of downloading the platform's whole bundle. It returns the same `AWSInstance` that
`get` does, or `None` if the platform has no instance with that name:

```python
from infrawrench_bulk_instances import fetch_aws_instance

m5 = fetch_aws_instance("ec2", "m5.large")
if m5 is not None:
    len(m5.pricing.on_demand)
```

It takes `token` like the bundle download, and `base_url` for where the API is served from
(`https://app.infrawrench.com` by default). Nothing is cached. The API syncs each new bundle within
about half an hour of it being published, so it can briefly trail `download_aws_pricing_data`.

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`cache_path`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Each platform's bundle is cached
under its own name (`rds-bundle-…json`), so loading one never evicts another. Pass
`cache_pricing_data=False` to always download and never touch the disk. The cache is
shared with the other Infrawrench bulk-instances SDKs.

Loading decompresses and parses the whole bundle. Instances are decoded lazily:
`get` only wraps the raw rows, and `attributes`, `attributes_history`, `pricing`
and `pricing_history` each decode on first access and keep the result. The
returned objects are shared between calls, so they are read-only: prices and
changes are frozen dataclasses, sequences are tuples and mappings are read-only
views (`attributes_in` returns a new `dict`).

## Prices and regions

- `region` is the AWS location name (`US East (N. Virginia)`), `region_code` its
  code (`us-east-1`) where the price list gives one, else `None`.
- `pricing` holds only what is still offered. In `pricing_history`, a `None`
  `hourly` means the price stopped being offered at `at`.
- Dates are timezone-aware UTC `datetime`s.
- Instances AWS no longer lists are still in `keys()`, with `deleted_at` set and
  empty `pricing`.
