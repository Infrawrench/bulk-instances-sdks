package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * Hetzner's Server Auction pricing data, keyed by listing ({@code 3107671}). It has the same members as
 * {@link AWSPricingData} and decodes the same way; see the README for what Hetzner's data holds.
 */
public final class HetznerAuctionPricingData extends PricingData<HetznerAuctionInstance> {
    HetznerAuctionPricingData(Bundle b) {
        super(b);
    }

    @Override
    HetznerAuctionInstance newInstance(String name, RawInstance raw) {
        return new HetznerAuctionInstance(name, raw, this);
    }

    /**
     * The listing with this name, or empty if the bundle has never listed it.
     *
     * @param listingId e.g. {@code 3107671}
     * @return the listing, the same object on every call
     */
    @Override
    public Optional<HetznerAuctionInstance> get(String listingId) {
        return super.get(listingId);
    }
}
