<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * Hetzner's cloud server pricing data, keyed by server type (`cx23`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what Hetzner's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class HetznerPricingData extends AWSPricingData
{
    /**
     * The server type with this name, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $serverType): ?HetznerInstance
    {
        $instance = parent::get($serverType);
        assert($instance === null || $instance instanceof HetznerInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): HetznerInstance
    {
        return new HetznerInstance($name, $raw, $this);
    }
}
