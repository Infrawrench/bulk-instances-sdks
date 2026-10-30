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
