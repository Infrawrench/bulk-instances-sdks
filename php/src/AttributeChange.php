<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

final readonly class AttributeChange
{
    public function __construct(
        public \DateTimeImmutable $at,
        public string $key,
        /** `null` means the attribute was removed. */
        public ?string $value,
        /** The AWS location this change applies to, or `null` for every region. */
        public ?string $region,
    ) {
    }
}
