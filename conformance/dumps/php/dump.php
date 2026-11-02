<?php

declare(strict_types=1);

require __DIR__ . '/vendor/autoload.php';

use Infrawrench\BulkInstances\AlibabaInstance;
use Infrawrench\BulkInstances\AlibabaPricingData;
use Infrawrench\BulkInstances\AlibabaPricingDataException;
use Infrawrench\BulkInstances\AWSInstance;
use Infrawrench\BulkInstances\AWSPricingData;
use Infrawrench\BulkInstances\AWSPricingDataException;
use Infrawrench\BulkInstances\AzureInstance;
use Infrawrench\BulkInstances\AzurePricingData;
use Infrawrench\BulkInstances\AzurePricingDataException;
use Infrawrench\BulkInstances\BulkInstances;
use Infrawrench\BulkInstances\GCPInstance;
use Infrawrench\BulkInstances\GCPPricingData;
use Infrawrench\BulkInstances\GCPPricingDataException;
use Infrawrench\BulkInstances\RunpodInstance;
use Infrawrench\BulkInstances\RunpodPricingData;
use Infrawrench\BulkInstances\RunpodPricingDataException;

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

// RunPod, Alibaba, Azure and GCP have their own methods and types, and their own exceptions.
/** @param class-string<AWSPricingDataException> $exception */
$providerError = static function (AWSPricingDataException $e, string $exception) use ($error): never {
    if (!$e instanceof $exception) {
        fwrite(STDERR, 'expected a ' . $exception . ', got ' . $e::class . "\n");
        exit(1);
    }
    $error($e);
};
/**
 * @param class-string<AWSPricingData> $dataClass
 * @param class-string<AWSInstance> $instanceClass
 */
$expectTypes = static function (AWSPricingData $d, string $dataClass, string $instanceClass): void {
    $first = $d->keys()[0] ?? null;
    if (!$d instanceof $dataClass || ($first !== null && !$d->get($first) instanceof $instanceClass)) {
        fwrite(STDERR, "expected $dataClass and $instanceClass\n");
        exit(1);
    }
};

/** @param class-string<AWSInstance> $instanceClass */
$expectInstance = static function (?AWSInstance $i, string $instanceClass): void {
    if ($i !== null && !$i instanceof $instanceClass) {
        fwrite(STDERR, "expected $instanceClass\n");
        exit(1);
    }
};

if ($instanceType !== null) {
    $apiOptions = ['token' => $token === '-' ? null : $token, 'baseUrl' => $baseUrl];
    if ($platform === 'runpod') {
        try {
            $i = BulkInstances::fetchRunpodInstance($instanceType, ...$apiOptions);
        } catch (AWSPricingDataException $e) {
            $providerError($e, RunpodPricingDataException::class);
        }
        $expectInstance($i, RunpodInstance::class);
    } elseif ($platform === 'alibaba') {
        try {
            $i = BulkInstances::fetchAlibabaInstance($instanceType, ...$apiOptions);
        } catch (AWSPricingDataException $e) {
            $providerError($e, AlibabaPricingDataException::class);
        }
        $expectInstance($i, AlibabaInstance::class);
    } else {
        try {
            $i = BulkInstances::fetchAwsInstance($platform, $instanceType, ...$apiOptions);
        } catch (AWSPricingDataException $e) {
            $error($e);
        }
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

$options = ['token' => $token === '-' ? null : $token, 'cachePricingData' => $cache === '1', 'cachePath' => $cachePath, 'baseUrl' => $baseUrl];
try {
    if ($platform === 'runpod') {
        try {
            $data = BulkInstances::downloadRunpodPricingData(...$options);
        } catch (AWSPricingDataException $e) {
            $providerError($e, RunpodPricingDataException::class);
        }
        $expectTypes($data, RunpodPricingData::class, RunpodInstance::class);
    } elseif ($platform === 'alibaba') {
        try {
            $data = BulkInstances::downloadAlibabaPricingData(...$options);
        } catch (AWSPricingDataException $e) {
            $providerError($e, AlibabaPricingDataException::class);
        }
        $expectTypes($data, AlibabaPricingData::class, AlibabaInstance::class);
    } elseif ($platform === 'azure') {
        try {
            $data = BulkInstances::downloadAzurePricingData(...$options);
        } catch (AWSPricingDataException $e) {
            $providerError($e, AzurePricingDataException::class);
        }
        $expectTypes($data, AzurePricingData::class, AzureInstance::class);
    } elseif ($platform === 'gcp') {
        try {
            $data = BulkInstances::downloadGcpPricingData(...$options);
        } catch (AWSPricingDataException $e) {
            $providerError($e, GCPPricingDataException::class);
        }
        $expectTypes($data, GCPPricingData::class, GCPInstance::class);
    } else {
        $data = $platform === null
            ? BulkInstances::downloadAwsEc2PricingData(...$options)
            : BulkInstances::downloadAwsPricingData($platform, ...$options);
    }
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
