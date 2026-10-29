<?php

declare(strict_types=1);

require __DIR__ . '/vendor/autoload.php';

use Infrawrench\BulkInstances\AWSPricingDataException;
use Infrawrench\BulkInstances\BulkInstances;

[, $baseUrl, $cachePath, $token, $cache] = $argv;
$ts = static fn (?DateTimeImmutable $d) => $d?->getTimestamp();
$row = static function (object $r) use ($ts): array {
    $out = get_object_vars($r);
    foreach (['at', 'since'] as $k) {
        if (array_key_exists($k, $out)) {
            $out[$k] = $ts($out[$k]);
        }
    }
    return $out;
};

try {
    $data = BulkInstances::downloadAwsEc2PricingData(
        token: $token === '-' ? null : $token,
        cachePricingData: $cache === '1',
        cachePath: $cachePath,
        baseUrl: $baseUrl,
    );
} catch (AWSPricingDataException $e) {
    echo json_encode(['error' => ['status' => $e->status, 'message' => $e->getMessage()]]), "\n";
    exit(3);
}

$obj = static fn (array $a) => (object) $a;
$regions = array_map($obj, $data->regions());
$keys = $data->keys();
sort($keys, SORT_STRING);
$out = [
    'snapshots' => array_map($ts, $data->snapshots()),
    'regions' => (object) $regions,
    'keys' => $keys,
    'has' => ['m5.large' => $data->has('m5.large'), 'nope' => $data->has('nope')],
    'getMissing' => $data->get('nope'),
    'instances' => new stdClass(),
];
foreach ($data->keys() as $k) {
    $i = $data->get($k);
    $p = $i->pricing();
    $h = $i->pricingHistory();
    $in = [];
    foreach ([...array_keys($regions), 'Mystery', 'Nowhere'] as $r) {
        $in[$r] = (object) $i->attributesIn((string) $r);
    }
    $out['instances']->$k = [
        'name' => $i->name,
        'createdAt' => $ts($i->createdAt()),
        'deletedAt' => $ts($i->deletedAt()),
        'attributes' => (object) $i->attributes(),
        'attributesIn' => (object) $in,
        'attributesHistory' => array_map($row, $i->attributesHistory()),
        'pricing' => ['onDemand' => array_map($row, $p->onDemand), 'reserved' => array_map($row, $p->reserved)],
        'pricingHistory' => ['onDemand' => array_map($row, $h->onDemand), 'reserved' => array_map($row, $h->reserved)],
    ];
    // Same instance object every time, and memoized parts are shared.
    if ($data->get($k) !== $i || $i->pricing() !== $p || $i->pricingHistory() !== $h) {
        fwrite(STDERR, "not memoized: $k\n");
        exit(1);
    }
}
if ($data->snapshots() !== [] && $data->snapshots()[0]->getTimezone()->getName() !== 'UTC') {
    fwrite(STDERR, "snapshots are not UTC\n");
    exit(1);
}
echo json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRESERVE_ZERO_FRACTION | JSON_THROW_ON_ERROR), "\n";
