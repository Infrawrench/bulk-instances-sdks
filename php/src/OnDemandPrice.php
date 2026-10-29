<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

final readonly class OnDemandPrice
{
    public function __construct(
        /** The AWS location name, e.g. `US East (N. Virginia)`. */
        public string $region,
        /** e.g. `us-east-1`. `null` for locations the price list never gave a code. */
        public ?string $regionCode,
        public string $operatingSystem,
        public string $tenancy,
        public string $licenseModel,
        public string $preInstalledSw,
        public string $capacitystatus,
        /** USD per hour. */
        public float $hourly,
        /** When this price took effect. */
        public \DateTimeImmutable $since,
    ) {
    }
}
