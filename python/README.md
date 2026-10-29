# infrawrench-bulk-instances

AWS EC2 instance attributes and prices, with their full history, from the bundle
Infrawrench publishes at `instances-bundles.infrawrench.com`.

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

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`cache_path`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Pass `cache_pricing_data=False`
to always download and never touch the disk. The cache is shared with the other
Infrawrench bulk-instances SDKs.

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
