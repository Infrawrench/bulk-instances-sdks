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
