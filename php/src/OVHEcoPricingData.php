<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * OVHcloud's eco dedicated server pricing data, keyed by server (`24sys01`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what OVHcloud's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class OVHEcoPricingData extends AWSPricingData
{
    /**
     * The server with this name, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $server): ?OVHEcoInstance
    {
        $instance = parent::get($server);
        assert($instance === null || $instance instanceof OVHEcoInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): OVHEcoInstance
    {
        return new OVHEcoInstance($name, $raw, $this);
    }
}
