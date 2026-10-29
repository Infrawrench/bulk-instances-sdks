# infrawrench-bulk_instances

AWS EC2 instance attributes and prices, with their full history, from the bundle
Infrawrench publishes at `instances-bundles.infrawrench.com`.

```sh
gem install infrawrench-bulk_instances
```

```ruby
require "infrawrench/bulk_instances"

data = Infrawrench::BulkInstances.download_aws_ec2_pricing_data(token: ENV["INFRAWRENCH_API_KEY"])

data.keys # ["m5.large", "t2.micro", ...]

m5 = data["m5.large"]
m5.attributes["vcpu"] # "2"
m5.attributes_in("US East (N. Virginia)") # with that region's overrides
m5.pricing.on_demand.find do |p|
  p.region_code == "us-east-1" && p.operating_system == "Linux" && p.tenancy == "Shared" &&
    p.pre_installed_sw == "NA" && p.capacitystatus == "Used"
end&.hourly # 0.096

m5.attributes_history # every attribute change, oldest first
m5.pricing_history.reserved # every reserved price change, oldest first
```

Any Infrawrench bearer credential works as `token:` (an `iwk_` API key, an agent
credential or a WorkOS access token). It defaults to `INFRAWRENCH_API_KEY`.

Requires Ruby 3.2 or later, and liblzma (part of macOS and of practically every
Linux distribution; `xz-utils`/`xz` otherwise) to decompress downloads.

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`cache_path:`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Pass `cache_pricing_data: false`
to always download and never touch the disk. The cache is shared with the other
Infrawrench SDKs.

Loading decompresses and parses the whole bundle. Instances are decoded lazily:
`get` only wraps the raw rows, and `attributes`, `attributes_history`, `pricing`
and `pricing_history` each decode on first access and keep the result. The
returned objects are shared between calls, so they are frozen. Memoization is not
synchronized: threads racing on a first access may decode the same part twice,
which is harmless.

Failures raise `Infrawrench::BulkInstances::AWSPricingDataError`, whose `status`
is the HTTP status if there was a response.

## Prices and regions

- `region` is the AWS location name (`US East (N. Virginia)`), `region_code` its
  code (`us-east-1`) where the price list gives one, else `nil`.
- `pricing` holds only what is still offered. In `pricing_history`, a `nil`
  `hourly` means the price stopped being offered at `at`.
- Times are UTC `Time`s.
- Instances AWS no longer lists are still in `keys`, with `deleted_at` set and
  empty `pricing`.
