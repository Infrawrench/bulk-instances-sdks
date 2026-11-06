package com.infrawrench.bulkinstances;

/** One Hetzner Server Auction listing. It has the same members as {@link AWSInstance}, which it extends. */
public final class HetznerAuctionInstance extends AWSInstance {
    HetznerAuctionInstance(String name, RawInstance raw, HetznerAuctionPricingData data) {
        super(name, raw, data);
    }
}
