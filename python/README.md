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
