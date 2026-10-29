<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

final readonly class ReservedPrice
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
        public string $leaseContractLength,
        public string $offeringClass,
        public string $purchaseOption,
        /** USD per hour. */
        public float $hourly,
        /** USD paid up front. */
        public float $upfront,
        public \DateTimeImmutable $since,
    ) {
    }
}
