<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

final readonly class OnDemandPriceChange
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
        public \DateTimeImmutable $at,
        /** `null` means no longer offered from `$at` on. */
        public ?float $hourly,
    ) {
    }
}
