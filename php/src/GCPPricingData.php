<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * Google Cloud's Compute Engine pricing data, keyed by machine type (`n2-standard-2`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what Google Cloud's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class GCPPricingData extends AWSPricingData
{
    /**
     * The machine type with this name, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $machineType): ?GCPInstance
    {
        $instance = parent::get($machineType);
        assert($instance === null || $instance instanceof GCPInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): GCPInstance
    {
        return new GCPInstance($name, $raw, $this);
    }
}
