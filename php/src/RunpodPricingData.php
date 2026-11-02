<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * RunPod's pricing data, keyed by GPU type id (`NVIDIA H100 80GB HBM3`) or CPU pod id (`cpu3c-2-4`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what RunPod's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class RunpodPricingData extends AWSPricingData
{
    /**
     * The GPU type or CPU pod with this id, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $instanceType): ?RunpodInstance
    {
        $instance = parent::get($instanceType);
        assert($instance === null || $instance instanceof RunpodInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): RunpodInstance
    {
        return new RunpodInstance($name, $raw, $this);
    }
}
