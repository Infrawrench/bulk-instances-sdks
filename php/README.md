# infrawrench/bulk-instances

AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full
history, from the bundles Infrawrench publishes at `instances-bundles.infrawrench.com`.

```sh
composer require infrawrench/bulk-instances
```

Requires PHP 8.2+ with `ext-curl` and `ext-json`, plus either the xz PECL extension
or the `xz` command (see [Caching](#caching)).

```php
use Infrawrench\BulkInstances\BulkInstances;

$data = BulkInstances::downloadAwsEc2PricingData(token: getenv('INFRAWRENCH_API_KEY') ?: null);

$data->keys(); // ['m5.large', 't2.micro', ...]

$m5 = $data->get('m5.large');
$m5->attributes()['vcpu']; // '2'
$m5->attributesIn('US East (N. Virginia)'); // with that region's overrides
foreach ($m5->pricing()->onDemand as $p) {
    if ($p->regionCode === 'us-east-1' && $p->operatingSystem === 'Linux' && $p->tenancy === 'Shared'
        && $p->preInstalledSw === 'NA' && $p->capacitystatus === 'Used') {
        echo $p->hourly; // 0.096
    }
}

$m5->attributesHistory(); // every attribute change, oldest first
$m5->pricingHistory()->reserved; // every reserved price change, oldest first
```

Any Infrawrench bearer credential works as `token` (an `iwk_` API key, an agent
credential or a WorkOS access token). It defaults to `INFRAWRENCH_API_KEY`. When
the data cannot be downloaded, `AWSPricingDataException` is thrown; its `status`
is the HTTP status, if there was a response.

## Other AWS platforms

`BulkInstances::downloadAwsPricingData($platform, ...)` loads any platform's bundle;
`BulkInstances::downloadAwsEc2PricingData(...)` is the same as `downloadAwsPricingData('ec2', ...)`.
`BulkInstances::AWS_PLATFORMS` lists the platforms:

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

The fields that pick a price differ by platform. `$data->variantKeys()` names them, and every
price has a `$variant` array keyed by them:

```php
use Infrawrench\BulkInstances\BulkInstances;

$rds = BulkInstances::downloadAwsPricingData('rds');
$rds->variantKeys(); // ['databaseEngine', 'databaseEdition', 'licenseModel', 'deploymentOption', ...]
foreach ($rds->get('db.m5.large')->pricing()->onDemand as $p) {
    if ($p->regionCode === 'us-east-1' && $p->variant['databaseEngine'] === 'MySQL'
        && $p->variant['deploymentOption'] === 'Multi-AZ') {
        echo $p->hourly;
    }
}
```

`operatingSystem`, `tenancy`, `licenseModel`, `preInstalledSw` and `capacitystatus` are EC2's
variant fields. On other platforms they are `''`, unless the platform has a field with that name
(RDS has `licenseModel`).

`spot` is EC2's spot prices. They are in `pricing()->onDemand`, one per region and `operatingSystem` (`Linux` or
`Windows`): the lowest price across the region's availability zones, as AWS's Spot pricing page shows it.
Its locations are region codes, so `region` and `regionCode` are both `us-east-1`. Spot instances
have no attributes; take their specs from `ec2`. The history goes back to August 2026, hourly at
first and every 6 hours since November 2026, and prices change far more often than on-demand prices.

## RunPod

`BulkInstances::downloadRunpodPricingData(...)` loads RunPod's GPU and CPU pod prices. It takes the same
named parameters as the AWS methods (minus `$platform`), caches the same way, and throws a
`RunpodPricingDataException`, a subclass of `AWSPricingDataException`. It returns a `RunpodPricingData`, whose
`get()` returns a `RunpodInstance`; they have the same members as `AWSPricingData` and `AWSInstance`.

```php
$runpod = BulkInstances::downloadRunpodPricingData();
foreach ($runpod->get('NVIDIA H100 80GB HBM3')?->pricing()->onDemand ?? [] as $p) {
    if ($p->variant['cloudType'] === 'Secure Cloud') {
        echo $p->hourly;
    }
}
```

It has GPU types by RunPod's id (`NVIDIA H100 80GB HBM3`), priced per GPU per hour, and CPU pods by pod id
(`cpu3c-2-4`: flavor, vCPUs, GB of memory), priced per pod per hour; the `productFamily` attribute is `GPU` or
`CPU`. Prices are the same in every data center, so every price is in the location `global`. The only variant
key is `cloudType`, `Secure Cloud` or `Community Cloud`. Savings plans are in `pricing()->reserved` with the term
`3mo` or `6mo`, `Savings Plan`, `All Upfront`, and `hourly` is the plan's effective hourly rate. Stock levels
and spot prices are not included. The history starts in November 2026.

## Alibaba Cloud

`BulkInstances::downloadAlibabaPricingData(...)` loads Alibaba Cloud ECS prices. It takes the same named
parameters as the AWS methods (minus `$platform`), caches the same way, and throws an
`AlibabaPricingDataException`, a subclass of `AWSPricingDataException`. It returns an `AlibabaPricingData`, whose
`get()` returns an `AlibabaInstance`; they have the same members as `AWSPricingData` and `AWSInstance`.

```php
$alibaba = BulkInstances::downloadAlibabaPricingData();
foreach ($alibaba->get('ecs.g6.large')?->pricing()->onDemand ?? [] as $p) {
    if ($p->regionCode === 'cn-hangzhou' && $p->variant['operatingSystem'] === 'Linux'
        && $p->variant['networkType'] === 'VPC') {
        echo $p->hourly;
    }
}
```

Its locations are region ids (`cn-hangzhou`), so the location and its region code are the same, and `regions()`
gives each an English `name`. Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `networkType`
(`VPC`, or `Classic` in older history). `pricing()->onDemand` has pay-as-you-go prices. `pricing()->reserved` has
subscriptions, with the term `1mo` or `1yr` to `5yr`, `Subscription`, `All Upfront`: they are paid in full
when bought, so `hourly` is 0 and `upfront` is the price. It also has reserved instances, with the term `1yr` or
`3yr`, `Reserved Instance`, and a purchase option. Attributes are Alibaba's instance type definitions
(`CpuCoreCount`, `MemorySize`, `CpuOptions.ThreadsPerCore`, ...), from May 2023 on. The history starts in
May 2018.

## Azure

`BulkInstances::downloadAzurePricingData(...)` loads Azure virtual machine prices. It takes the same named
parameters as the AWS methods (minus `$platform`), caches the same way, and throws an
`AzurePricingDataException`, a subclass of `AWSPricingDataException`. It returns an `AzurePricingData`, whose
`get()` returns an `AzureInstance`; they have the same members as `AWSPricingData` and `AWSInstance`.

```php
$azure = BulkInstances::downloadAzurePricingData();
foreach ($azure->get('Standard_D2s_v3')?->pricing()->onDemand ?? [] as $p) {
    if ($p->regionCode === 'eastus' && $p->variant['operatingSystem'] === 'Linux'
        && $p->variant['priority'] === 'Regular') {
        echo $p->hourly;
    }
}
```

It has VM sizes by ARM name (`Standard_D2s_v3`), priced per VM per hour. Its locations are ARM region names
(`eastus`), so the location and its region code are the same, and `regions()` gives each Azure's display
`name` (`US East`). Its variant keys are `operatingSystem` (`Linux` or `Windows`) and `priority` (`Regular`,
`Spot` or `Low Priority`). `pricing()->onDemand` has pay-as-you-go prices, dated by when Azure says they took
effect. `pricing()->reserved` has reservations, with the term `1yr`, `3yr` or `5yr`, `Reserved Instance`,
`All Upfront`: `hourly` is 0 and `upfront` is the whole term's price. Azure lists reservations under `Linux`
only; on Windows the license is billed on top. It also has savings plans, with the term `1yr` or `3yr`,
`Savings Plan`, `No Upfront`, and `hourly` is the plan's rate. Attributes are `skuName`, `productName` and,
from Azure's pricing calculator, `cores`, `ram` (GB), `diskSize` (temporary disk, GB), `gpu` and `series`.
About a third of sizes, mostly the newest and retired series, have no calculator specs. Dedicated hosts are
not included. The history starts in November 2026.

## Google Cloud

`BulkInstances::downloadGcpPricingData(...)` loads Google Cloud Compute Engine prices. It takes the same named
parameters as the AWS methods (minus `$platform`), caches the same way, and throws a
`GCPPricingDataException`, a subclass of `AWSPricingDataException`. It returns a `GCPPricingData`, whose
`get()` returns a `GCPInstance`; they have the same members as `AWSPricingData` and `AWSInstance`.

```php
$gcp = BulkInstances::downloadGcpPricingData();
foreach ($gcp->get('n2-standard-2')?->pricing()->onDemand ?? [] as $p) {
    if ($p->regionCode === 'us-central1' && $p->variant['provisioningModel'] === 'Standard') {
        echo $p->hourly;
    }
}
```

It has machine types by name (`n2-standard-2`), priced per VM per hour. Google bills most machine types per
vCPU and per GiB of memory at their family's rates, plus their GPUs, so each price is worked out from those
rates and the machine type's shape. Prices leave out bundled Local SSD, OS licenses and sustained use
discounts, and TPU, X4, X5 and A4X machine types aren't included. Its locations are regions (`us-central1`),
so the location and its region code are the same. The only variant key is `provisioningModel`, `Standard` or
`Spot`. `pricing()->reserved` has committed use discounts, with the term `1yr` or `3yr`, `Committed Use`,
`No Upfront`, and `hourly` is the commitment's rate. Attributes are the machine type's fields from the Compute
Engine API (`guestCpus`, `memoryMb`, `description`, `isSharedCpu`, ...), `acceleratorType` and
`acceleratorCount` for its GPUs, and `zones`, the zones in each region that have it, which differ by region
(see `attributesIn($region)`). The history starts in November 2026.

`fetchAwsInstance` doesn't cover RunPod, Alibaba, Azure or Google Cloud; download their bundles instead.

## One instance

`BulkInstances::fetchAwsInstance($platform, $instanceType, ...)` fetches a single instance from the
Infrawrench API instead of downloading the platform's whole bundle. It returns the same
`AWSInstance` that `get()` does, or `null` if the platform has no instance with that name:

```php
$m5 = BulkInstances::fetchAwsInstance('ec2', 'm5.large');
count($m5?->pricing()->onDemand ?? []);
```

It takes `token` like the bundle download, and `baseUrl` for where the API is served from
(`https://app.infrawrench.com` by default). Nothing is cached. The API syncs each new bundle within
about half an hour of it being published, so it can briefly trail `downloadAwsPricingData()`.

## Caching

The bundle is downloaded xz-compressed (about 20 MB) and kept decompressed (about
210 MB) in `~/.infrawrench/aws_pricing_data` (`cachePath`), so a cached load skips
decompression. Each load asks the server which bundle is latest and downloads it
only if it is not cached, deleting the older one. If the server cannot be
reached, the newest cached bundle is used instead. Each platform's bundle is cached
under its own name (`rds-bundle-…json`), so loading one never evicts another. Pass
`cachePricingData: false` to always download and never touch the disk. The cache is shared with the other
Infrawrench SDKs.

Decompression uses the [xz PECL extension](https://pecl.php.net/package/xz) when it
is loaded, and otherwise pipes the download through the `xz` command (xz-utils:
`apt install xz-utils`, `brew install xz`). If neither is available, downloading
throws `AWSPricingDataException`; a cached load needs neither.

Loading decompresses the whole bundle and keeps its JSON in memory. Instances are
decoded lazily: `get()` only parses that instance's rows, and `attributes()`,
`attributesHistory()`, `pricing()` and `pricingHistory()` each decode on first
access and keep the result. The returned objects are shared between calls and
are immutable (`readonly` classes; arrays are returned by value).

A load peaks at about 260 MB and a decoded instance takes a few MB, so raise PHP's
default `memory_limit` of 128M: `512M` is enough to load the bundle and look at a
few dozen instance types. Decoding every instance takes about 5 GB.

## Prices and regions

- `region` is the AWS location name (`US East (N. Virginia)`), `regionCode` its
  code (`us-east-1`) where the price list gives one, `null` otherwise.
- `pricing()` holds only what is still offered. In `pricingHistory()`, a `null`
  `hourly` means the price stopped being offered at `at`.
- Instances AWS no longer lists are still in `keys()`, with `deletedAt()` set and
  empty `pricing()`.
- Dates are `DateTimeImmutable` in UTC.
