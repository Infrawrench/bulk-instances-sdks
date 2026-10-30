<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/** The product fields that pick a price. */
final readonly class Variant
{
    public function __construct(
        /** EC2's variant fields. For other platforms these are `""` unless the platform shares the field. */
        public string $operatingSystem,
        public string $tenancy,
        public string $licenseModel,
        public string $preInstalledSw,
        public string $capacitystatus,
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
