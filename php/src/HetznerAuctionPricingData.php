<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * Hetzner's Server Auction pricing data, keyed by listing (`3107671`).
 * It decodes the same way as {@see AWSPricingData}; see the README for what Hetzner's data holds.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class HetznerAuctionPricingData extends AWSPricingData
{
    /**
     * The listing with this name, or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $listingId): ?HetznerAuctionInstance
    {
        $instance = parent::get($listingId);
        assert($instance === null || $instance instanceof HetznerAuctionInstance);
        return $instance;
    }

    /** @param RawInstance $raw */
    protected function newInstance(string $name, array $raw): HetznerAuctionInstance
    {
        return new HetznerAuctionInstance($name, $raw, $this);
    }
}
