<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

final readonly class Pricing
{
    public function __construct(
        /** @var list<OnDemandPrice> */
        public array $onDemand,
        /** @var list<ReservedPrice> */
        public array $reserved,
    ) {
    }
}
