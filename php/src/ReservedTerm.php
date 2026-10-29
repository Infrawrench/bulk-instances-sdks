<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

final readonly class ReservedTerm
{
    public function __construct(
        public string $leaseContractLength,
        public string $offeringClass,
        public string $purchaseOption,
    ) {
    }
}
