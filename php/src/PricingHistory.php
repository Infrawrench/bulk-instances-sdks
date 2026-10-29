<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

final readonly class PricingHistory
{
    public function __construct(
        /** @var list<OnDemandPriceChange> Oldest first. */
        public array $onDemand,
        /** @var list<ReservedPriceChange> Oldest first. */
        public array $reserved,
    ) {
    }
}
