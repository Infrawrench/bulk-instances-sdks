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

## Other clouds

Infrawrench also publishes bundles for clouds other than AWS, in the same format, and `download_aws_pricing_data` loads them
the same way. `OTHER_PLATFORMS` lists them:

| Platform | What | History from |
| --- | --- | --- |
| `runpod` | RunPod GPU and CPU pods | November 2026 |
| `alibaba` | Alibaba Cloud ECS instance types | May 2018 |

```python
from infrawrench_bulk_instances import download_aws_pricing_data

runpod = download_aws_pricing_data("runpod")
h100 = runpod.get("NVIDIA H100 80GB HBM3")
assert h100 is not None
next(p.hourly for p in h100.pricing.on_demand if p.variant["cloudType"] == "Secure Cloud")
```

`runpod` has GPU types by RunPod's id (`NVIDIA H100 80GB HBM3`), priced per GPU per hour, and CPU pods by
pod id (`cpu3c-2-4`: flavor, vCPUs, GB of memory), priced per pod per hour; the `productFamily` attribute is
`GPU` or `CPU`. Prices are the same in every data center, so every price is in the location `global`. The
only variant key is `cloudType`, `Secure Cloud` or `Community Cloud`. Savings plans are in `pricing.reserved`
with the term `3mo` or `6mo`, `Savings Plan`, `All Upfront`, and `hourly` is the plan's effective hourly rate.
Stock levels and spot prices are not included.

`alibaba`'s locations are region ids (`cn-hangzhou`), so the location and its region code are the same, and
the regions table gives each an English `name`. Its variant keys are `operatingSystem` (`Linux` or `Windows`)
and `networkType` (`VPC`, or `Classic` in older history). `pricing.on_demand` has pay-as-you-go prices. `pricing.reserved` has
subscriptions, with the term `1mo` or `1yr` to `5yr`, `Subscription`, `All Upfront`: they are paid in full
when bought, so `hourly` is 0 and `upfront` is the price. It also has reserved instances, with the term `1yr` or
`3yr`, `Reserved Instance`, and a purchase option. Attributes are Alibaba's instance type definitions
(`CpuCoreCount`, `MemorySize`, `CpuOptions.ThreadsPerCore`, ...), from May 2023 on.

`fetch_aws_instance` doesn't serve these platforms yet: the Infrawrench API has no instances for them, so it returns
`None`. Download the bundle instead.

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
