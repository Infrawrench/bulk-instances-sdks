<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * IBM Cloud's Virtual Server for VPC pricing data, keyed by profile (`bx3d-2x10`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what IBM Cloud's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class IBMPricingData extends AWSPricingData
{
    /**
     * The profile with this name, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $profile): ?IBMInstance
    {
        $instance = parent::get($profile);
        assert($instance === null || $instance instanceof IBMInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): IBMInstance
    {
        return new IBMInstance($name, $raw, $this);
    }
}
