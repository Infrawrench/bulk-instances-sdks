<?php

declare(strict_types=1);

require __DIR__ . '/vendor/autoload.php';

use Infrawrench\BulkInstances\AWSInstance;
use Infrawrench\BulkInstances\AWSPricingDataException;
use Infrawrench\BulkInstances\BulkInstances;

[, $baseUrl, $cachePath, $token, $cache] = $argv;
$platform = $argv[5] ?? null;
$instanceType = $argv[6] ?? null;
$ts = static fn (?DateTimeImmutable $d) => $d?->getTimestamp();
$row = static function (object $r) use ($ts): array {
    $out = get_object_vars($r);
    if (array_key_exists('variant', $out)) {
        $out['variant'] = (object) $out['variant'];
    }
    foreach (['at', 'since'] as $k) {
        if (array_key_exists($k, $out)) {
            $out[$k] = $ts($out[$k]);
        }
    }
    return $out;
};

$error = static function (AWSPricingDataException $e): never {
    echo json_encode(['error' => ['status' => $e->status, 'message' => $e->getMessage()]]), "\n";
    exit(3);
};
$print = static function (mixed $out): void {
    echo json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRESERVE_ZERO_FRACTION | JSON_THROW_ON_ERROR), "\n";
};
/** @param list<string> $regionNames */
$dumpInstance = static function (AWSInstance $i, array $regionNames) use ($ts, $row): array {
    $p = $i->pricing();
    $h = $i->pricingHistory();
    $in = [];
    foreach ([...$regionNames, 'Mystery', 'Nowhere'] as $r) {
        $in[$r] = (object) $i->attributesIn((string) $r);
    }
    $out = [
        'name' => $i->name,
        'createdAt' => $ts($i->createdAt()),
        'deletedAt' => $ts($i->deletedAt()),
        'attributes' => (object) $i->attributes(),
        'attributesIn' => (object) $in,
        'attributesHistory' => array_map($row, $i->attributesHistory()),
        'pricing' => ['onDemand' => array_map($row, $p->onDemand), 'reserved' => array_map($row, $p->reserved)],
        'pricingHistory' => ['onDemand' => array_map($row, $h->onDemand), 'reserved' => array_map($row, $h->reserved)],
    ];
    // Memoized parts are shared.
    if ($i->pricing() !== $p || $i->pricingHistory() !== $h) {
        fwrite(STDERR, "not memoized: {$i->name}\n");
        exit(1);
    }
    return $out;
};

if ($instanceType !== null) {
    try {
        $i = BulkInstances::fetchAwsInstance($platform, $instanceType, token: $token === '-' ? null : $token, baseUrl: $baseUrl);
    } catch (AWSPricingDataException $e) {
        $error($e);
    }
    // The regions its attributes are overridden in; every other one is the same as `attributes`.
    $regionNames = [];
    foreach ($i?->attributesHistory() ?? [] as $c) {
        if ($c->region !== null) {
            $regionNames[$c->region] = true;
        }
    }
    $regionNames = array_map(strval(...), array_keys($regionNames));
    sort($regionNames, SORT_STRING);
    $print(['instance' => $i === null ? null : $dumpInstance($i, $regionNames)]);
    exit(0);
}

try {
    $options = ['token' => $token === '-' ? null : $token, 'cachePricingData' => $cache === '1', 'cachePath' => $cachePath, 'baseUrl' => $baseUrl];
    $data = $platform === null
        ? BulkInstances::downloadAwsEc2PricingData(...$options)
        : BulkInstances::downloadAwsPricingData($platform, ...$options);
} catch (AWSPricingDataException $e) {
    $error($e);
}

$obj = static fn (array $a) => (object) $a;
$regions = array_map($obj, $data->regions());
$keys = $data->keys();
sort($keys, SORT_STRING);
$out = [
    'offer' => $data->offer(),
    'variantKeys' => $data->variantKeys(),
    'snapshots' => array_map($ts, $data->snapshots()),
    'regions' => (object) $regions,
    'keys' => $keys,
    'has' => ['m5.large' => $data->has('m5.large'), 'nope' => $data->has('nope')],
    'getMissing' => $data->get('nope'),
    'instances' => new stdClass(),
];
foreach ($data->keys() as $k) {
    $i = $data->get($k);
    $out['instances']->$k = $dumpInstance($i, array_map(strval(...), array_keys($regions)));
    // Same instance object every time.
    if ($data->get($k) !== $i) {
        fwrite(STDERR, "not memoized: $k\n");
        exit(1);
    }
}
if ($data->snapshots() !== [] && $data->snapshots()[0]->getTimezone()->getName() !== 'UTC') {
    fwrite(STDERR, "snapshots are not UTC\n");
    exit(1);
}
$print($out);
