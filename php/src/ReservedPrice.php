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
        /** EC2's variant fields. For other platforms these are `""` unless the platform shares the field. */
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
        /**
         * Every field that picks the price, keyed by name, in {@see AWSPricingData::variantKeys()} order:
         * for RDS, `databaseEngine`, `deploymentOption` and so on.
         *
         * @var array<string, string>
         */
        public array $variant = [],
    ) {
    }
}
