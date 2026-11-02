# infrawrench-bulk_instances

AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full
history, from the bundles Infrawrench publishes at `instances-bundles.infrawrench.com`.

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

## Other AWS platforms

`download_aws_pricing_data(platform, **options)` loads any platform's bundle;
`download_aws_ec2_pricing_data(**options)` is the same as `download_aws_pricing_data("ec2", **options)`.
`Infrawrench::BulkInstances::AWS_PLATFORMS` lists the platforms:

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
price has a `variant` hash keyed by them:

```ruby
rds = Infrawrench::BulkInstances.download_aws_pricing_data("rds")
rds.variant_keys # ["databaseEngine", "databaseEdition", "licenseModel", "deploymentOption", ...]
rds["db.m5.large"].pricing.on_demand.find do |p|
  p.region_code == "us-east-1" && p.variant["databaseEngine"] == "MySQL" &&
    p.variant["deploymentOption"] == "Multi-AZ"
end&.hourly
```

`operating_system`, `tenancy`, `license_model`, `pre_installed_sw` and `capacitystatus` are EC2's
variant fields. On other platforms they are `""`, unless the platform has a field with that name
(RDS has `licenseModel`).

`spot` is EC2's spot prices. They are in `pricing.on_demand`, one per region and `operating_system` (`Linux` or
`Windows`): the lowest price across the region's availability zones, as AWS's Spot pricing page shows it.
Its locations are region codes, so `region` and `region_code` are both `us-east-1`. Spot instances
have no attributes; take their specs from `ec2`. The history goes back to August 2026, hourly at
first and every 6 hours since November 2026, and prices change far more often than on-demand prices.

Requires Ruby 3.2 or later, and liblzma (part of macOS and of practically every
Linux distribution; `xz-utils`/`xz` otherwise) to decompress downloads.

## RunPod

`download_runpod_pricing_data(**options)` loads RunPod's GPU and CPU pod prices. It takes the same options as
the AWS methods, caches the same way, and raises `RunpodPricingDataError`, a subclass of
`AWSPricingDataError`. It returns a `RunpodPricingData`, whose `get` (and `[]`) returns a `RunpodInstance`;
they have the same methods as `AWSPricingData` and `AWSInstance`.

```ruby
runpod = Infrawrench::BulkInstances.download_runpod_pricing_data
runpod["NVIDIA H100 80GB HBM3"].pricing.on_demand.find { |p| p.variant["cloudType"] == "Secure Cloud" }&.hourly
```

It has GPU types by RunPod's id (`NVIDIA H100 80GB HBM3`), priced per GPU per hour, and CPU pods by pod id
(`cpu3c-2-4`: flavor, vCPUs, GB of memory), priced per pod per hour; the `productFamily` attribute is `GPU` or
`CPU`. Prices are the same in every data center, so every price is in the location `global`. The only variant
key is `cloudType`, `Secure Cloud` or `Community Cloud`. Savings plans are in `pricing.reserved` with the term
`3mo` or `6mo`, `Savings Plan`, `All Upfront`, and `hourly` is the plan's effective hourly rate. Stock levels
and spot prices are not included. The history starts in November 2026.

## Alibaba Cloud

`download_alibaba_pricing_data(**options)` loads Alibaba Cloud ECS prices. It takes the same options as the
AWS methods, caches the same way, and raises `AlibabaPricingDataError`, a subclass of `AWSPricingDataError`.
It returns an `AlibabaPricingData`, whose `get` (and `[]`) returns an `AlibabaInstance`; they have the same
methods as `AWSPricingData` and `AWSInstance`.

```ruby
alibaba = Infrawrench::BulkInstances.download_alibaba_pricing_data
alibaba["ecs.g6.large"].pricing.on_demand.find do |p|
  p.region_code == "cn-hangzhou" && p.variant["operatingSystem"] == "Linux" && p.variant["networkType"] == "VPC"
end&.hourly
```

Its locations are region ids (`cn-hangzhou`), so the location and its region code are the same, and `regions`
gives each an English `name`. Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `networkType`
(`VPC`, or `Classic` in older history). `pricing.on_demand` has pay-as-you-go prices. `pricing.reserved` has
subscriptions, with the term `1mo` or `1yr` to `5yr`, `Subscription`, `All Upfront`: they are paid in full
when bought, so `hourly` is 0 and `upfront` is the price. It also has reserved instances, with the term `1yr` or
`3yr`, `Reserved Instance`, and a purchase option. Attributes are Alibaba's instance type definitions
(`CpuCoreCount`, `MemorySize`, `CpuOptions.ThreadsPerCore`, ...), from May 2023 on. The history starts in
May 2018.

`fetch_aws_instance` doesn't cover RunPod or Alibaba; download their bundles instead.

## One instance

`Infrawrench::BulkInstances.fetch_aws_instance(platform, instance_type, ...)` fetches a single
instance from the Infrawrench API instead of downloading the platform's whole bundle. It returns
the same `AWSInstance` that `get` does, or `nil` if the platform has no instance with that name:

```ruby
m5 = Infrawrench::BulkInstances.fetch_aws_instance("ec2", "m5.large")
m5&.pricing&.on_demand&.length
```

It takes `token:` like the bundle download, and `base_url:` for where the API is served from
(`https://app.infrawrench.com` by default). Nothing is cached. The API syncs each new bundle within
about half an hour of it being published, so it can briefly trail `download_aws_pricing_data`.

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`cache_path:`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Each platform's bundle is cached
under its own name (`rds-bundle-…json`), so loading one never evicts another. Pass `cache_pricing_data: false`
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
