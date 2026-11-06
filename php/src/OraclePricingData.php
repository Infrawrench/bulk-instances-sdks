<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * Oracle Cloud's compute pricing data, keyed by shape (`VM.Standard.E5.Flex-2-16`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what Oracle Cloud's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class OraclePricingData extends AWSPricingData
{
    /**
     * The shape with this name, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $shape): ?OracleInstance
    {
        $instance = parent::get($shape);
        assert($instance === null || $instance instanceof OracleInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): OracleInstance
    {
        return new OracleInstance($name, $raw, $this);
    }
}
