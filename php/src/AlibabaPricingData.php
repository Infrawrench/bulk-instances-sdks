<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * Alibaba Cloud's ECS pricing data, keyed by instance type (`ecs.g6.large`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what Alibaba's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class AlibabaPricingData extends AWSPricingData
{
    /**
     * The instance type with this name, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $instanceType): ?AlibabaInstance
    {
        $instance = parent::get($instanceType);
        assert($instance === null || $instance instanceof AlibabaInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): AlibabaInstance
    {
        return new AlibabaInstance($name, $raw, $this);
    }
}
