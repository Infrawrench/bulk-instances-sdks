# infrawrench-bulk-instances

AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full
history, from the bundles Infrawrench publishes at `instances-bundles.infrawrench.com`.

```sh
cargo add infrawrench-bulk-instances
```

```rust no_run
use infrawrench_bulk_instances::{Options, download_aws_ec2_pricing_data};

fn main() -> Result<(), infrawrench_bulk_instances::Error> {
    let data = download_aws_ec2_pricing_data(&Options {
        token: std::env::var("INFRAWRENCH_API_KEY").ok(),
        ..Options::default()
    })?;

    let types: Vec<&str> = data.keys().collect(); // ["m5.large", "t2.micro", ...]

    let m5 = data.get("m5.large").unwrap();
    let vcpu = &m5.attributes()["vcpu"]; // "2"
    let in_use1 = m5.attributes_in("US East (N. Virginia)"); // with that region's overrides
    let hourly = m5
        .pricing()
        .on_demand
        .iter()
        .find(|p| {
            p.region_code.as_deref() == Some("us-east-1")
                && p.variant.operating_system == "Linux"
                && p.variant.tenancy == "Shared"
                && p.variant.pre_installed_sw == "NA"
                && p.variant.capacitystatus == "Used"
        })
        .map(|p| p.hourly); // Some(0.096)

    let changes = m5.attributes_history(); // every attribute change, oldest first
    let reserved = &m5.pricing_history().reserved; // every reserved price change, oldest first
    Ok(())
}
```

Any Infrawrench bearer credential works as `token` (an `iwk_` API key, an agent
credential or a WorkOS access token). It defaults to `INFRAWRENCH_API_KEY`.

`download_aws_ec2_pricing_data` blocks. From async code, run it on a blocking
thread (e.g. `tokio::task::spawn_blocking`). The returned `AwsPricingData` is
`Send + Sync`.

## Other AWS platforms

`download_aws_pricing_data(platform, &options)` loads any platform's bundle;
`download_aws_ec2_pricing_data(&options)` is the same as
`download_aws_pricing_data("ec2", &options)`. `AWS_PLATFORMS` lists them:

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

The fields that pick a price differ by platform. `data.variant_keys()` names them, and
every price's `variant.fields` holds them as `(key, value)` pairs in that order:

```rust no_run
use infrawrench_bulk_instances::{Options, download_aws_pricing_data};

fn main() -> Result<(), infrawrench_bulk_instances::Error> {
    let rds = download_aws_pricing_data("rds", &Options::default())?;
    let keys = rds.variant_keys(); // ["databaseEngine", "databaseEdition", "licenseModel", "deploymentOption", ...]
    let hourly = rds
        .get("db.m5.large")
        .unwrap()
        .pricing()
        .on_demand
        .iter()
        .find(|p| {
            p.region_code.as_deref() == Some("us-east-1")
                && p.variant.get("databaseEngine") == Some("MySQL")
                && p.variant.get("deploymentOption") == Some("Multi-AZ")
        })
        .map(|p| p.hourly);
    Ok(())
}
```

`operating_system`, `tenancy`, `license_model`, `pre_installed_sw` and `capacitystatus` are
EC2's variant fields. On other platforms they are `""`, unless the platform has a field with
that name (RDS has `licenseModel`).

`spot` is EC2's spot prices. They are in `pricing().on_demand`, one per region and `operating_system` (`Linux` or
`Windows`): the lowest price across the region's availability zones, as AWS's Spot pricing page shows it.
Its locations are region codes, so `region` and `region_code` are both `us-east-1`. Spot instances
have no attributes; take their specs from `ec2`. The history goes back to August 2026, hourly at
first and every 6 hours since November 2026, and prices change far more often than on-demand prices.

## RunPod

`download_runpod_pricing_data(&options)` loads RunPod's GPU and CPU pod prices. It takes the same `Options` as
the AWS functions, caches the same way, and fails with the same `Error`. It returns a `RunpodPricingData`,
whose `get` returns a `&RunpodInstance`; they deref to `AwsPricingData` and `AwsInstance`, so they have the
same methods.

```rust no_run
use infrawrench_bulk_instances::{Options, download_runpod_pricing_data};

fn main() -> Result<(), infrawrench_bulk_instances::Error> {
    let runpod = download_runpod_pricing_data(&Options::default())?;
    let hourly = runpod
        .get("NVIDIA H100 80GB HBM3")
        .and_then(|h100| {
            h100.pricing()
                .on_demand
                .iter()
                .find(|p| p.variant.get("cloudType") == Some("Secure Cloud"))
        })
        .map(|p| p.hourly);
    Ok(())
}
```

It has GPU types by RunPod's id (`NVIDIA H100 80GB HBM3`), priced per GPU per hour, and CPU pods by pod id
(`cpu3c-2-4`: flavor, vCPUs, GB of memory), priced per pod per hour; the `productFamily` attribute is `GPU` or
`CPU`. Prices are the same in every data center, so every price is in the location `global`. The only variant
key is `cloudType`, `Secure Cloud` or `Community Cloud`. Savings plans are in `pricing().reserved` with the term
`3mo` or `6mo`, `Savings Plan`, `All Upfront`, and `hourly` is the plan's effective hourly rate. Stock levels
and spot prices are not included. The history starts in November 2026.

`fetch_runpod_instance(id, &options)` fetches one GPU type or CPU pod from the Infrawrench API instead (see
[One instance](#one-instance)). It returns an owned `RunpodInstance`, or `None` if RunPod has no instance with
that id:

```rust no_run
use infrawrench_bulk_instances::{AwsInstanceOptions, fetch_runpod_instance};

fn main() -> Result<(), infrawrench_bulk_instances::Error> {
    let h100 = fetch_runpod_instance("NVIDIA H100 80GB HBM3", &AwsInstanceOptions::default())?;
    Ok(())
}
```

## Alibaba Cloud

`download_alibaba_pricing_data(&options)` loads Alibaba Cloud ECS prices. It takes the same `Options` as the
AWS functions, caches the same way, and fails with the same `Error`. It returns an `AlibabaPricingData`, whose
`get` returns an `&AlibabaInstance`; they deref to `AwsPricingData` and `AwsInstance`, so they have the same
methods.

```rust no_run
use infrawrench_bulk_instances::{Options, download_alibaba_pricing_data};

fn main() -> Result<(), infrawrench_bulk_instances::Error> {
    let alibaba = download_alibaba_pricing_data(&Options::default())?;
    let hourly = alibaba
        .get("ecs.g6.large")
        .and_then(|g6| {
            g6.pricing().on_demand.iter().find(|p| {
                p.region_code.as_deref() == Some("cn-hangzhou")
                    && p.variant.get("operatingSystem") == Some("Linux")
                    && p.variant.get("networkType") == Some("VPC")
            })
        })
        .map(|p| p.hourly);
    Ok(())
}
```

Its locations are region ids (`cn-hangzhou`), so `region` and `region_code` are the same, and `regions()` gives
each an English `name`. Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `networkType` (`VPC`,
or `Classic` in older history). `pricing().on_demand` has pay-as-you-go prices. `pricing().reserved` has
subscriptions, with the term `1mo` or `1yr` to `5yr`, `Subscription`, `All Upfront`: they are paid in full when
bought, so `hourly` is 0 and `upfront` is the price. It also has reserved instances, with the term `1yr` or
`3yr`, `Reserved Instance`, and a purchase option. Attributes are Alibaba's instance type definitions
(`CpuCoreCount`, `MemorySize`, `CpuOptions.ThreadsPerCore`, ...), from May 2023 on. The history starts in
May 2018.

`fetch_alibaba_instance(instance_type, &options)` fetches one instance type from the Infrawrench API instead
(see [One instance](#one-instance)). It returns an owned `AlibabaInstance`, or `None` if Alibaba has no instance
type with that name:

```rust no_run
use infrawrench_bulk_instances::{AwsInstanceOptions, fetch_alibaba_instance};

fn main() -> Result<(), infrawrench_bulk_instances::Error> {
    let g6 = fetch_alibaba_instance("ecs.g6.large", &AwsInstanceOptions::default())?;
    Ok(())
}
```

## One instance

`fetch_aws_instance(platform, instance_type, &options)` fetches a single instance from the
Infrawrench API instead of downloading the platform's whole bundle. It returns the same
`AwsInstance` that `get` does, owned, or `None` if the platform has no instance with that name:

```rust no_run
use infrawrench_bulk_instances::{AwsInstanceOptions, fetch_aws_instance};

fn main() -> Result<(), infrawrench_bulk_instances::Error> {
    if let Some(m5) = fetch_aws_instance("ec2", "m5.large", &AwsInstanceOptions::default())? {
        let prices = m5.pricing().on_demand.len();
    }
    Ok(())
}
```

`AwsInstanceOptions` takes `token` like the bundle download, and `base_url` for where the API
is served from (`https://app.infrawrench.com` by default). Nothing is cached. The API syncs each
new bundle within about half an hour of it being published, so it can briefly trail
`download_aws_pricing_data`. Like the download, it blocks.

`fetch_runpod_instance(id, &options)` and `fetch_alibaba_instance(instance_type, &options)` do the same for
RunPod and Alibaba Cloud, with the same `AwsInstanceOptions`, the same `Error` and the same half-hour sync.
They return an owned `RunpodInstance` or `AlibabaInstance` (or `None`), which deref to `AwsInstance`. RunPod's
ids have spaces; pass them as they are, they are escaped for you.

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`cache_path`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Each platform's bundle is cached
under its own name (`rds-bundle-…json`), so loading one never evicts another. Set
`cache_pricing_data: false` to always download and never touch the disk.

Loading decompresses and parses the whole bundle. Instances are decoded lazily:
`get` only wraps the raw rows, and `attributes`, `attributes_history`, `pricing`
and `pricing_history` each decode on first access and keep the result. They are
shared between calls, so they are handed out as shared references.

## Prices and regions

- `region` is the AWS location name (`US East (N. Virginia)`), `region_code` its
  code (`us-east-1`) where the price list gives one.
- `pricing` holds only what is still offered. In `pricing_history`, a `None`
  `hourly` means the price stopped being offered at `at`.
- Instances AWS no longer lists are still in `keys()`, with `deleted_at` set and
  empty `pricing`.
