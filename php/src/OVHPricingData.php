<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * OVHcloud's Public Cloud pricing data, keyed by flavor (`b3-8`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what OVHcloud's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class OVHPricingData extends AWSPricingData
{
    /**
     * The flavor with this name, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $flavor): ?OVHInstance
    {
        $instance = parent::get($flavor);
        assert($instance === null || $instance instanceof OVHInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): OVHInstance
    {
        return new OVHInstance($name, $raw, $this);
    }
}
