<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * Azure's virtual machine pricing data, keyed by VM size (`Standard_D2s_v3`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what Azure's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class AzurePricingData extends AWSPricingData
{
    /**
     * The VM size with this name, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $size): ?AzureInstance
    {
        $instance = parent::get($size);
        assert($instance === null || $instance instanceof AzureInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): AzureInstance
    {
        return new AzureInstance($name, $raw, $this);
    }
}
