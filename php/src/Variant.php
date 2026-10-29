<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/** The product fields that pick a price. */
final readonly class Variant
{
    public function __construct(
        public string $operatingSystem,
        public string $tenancy,
        public string $licenseModel,
        public string $preInstalledSw,
        public string $capacitystatus,
    ) {
    }
}
