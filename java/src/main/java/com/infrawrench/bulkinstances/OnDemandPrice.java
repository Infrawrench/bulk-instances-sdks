package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

import java.time.Instant;

/**
 * A current on-demand price.
 *
 * @param location where the price applies
 * @param variant the product fields that pick the price
 * @param hourly USD per hour.
 * @param since when this price took effect.
 */
public record OnDemandPrice(Location location, Variant variant, double hourly, Instant since) {
    /** Rejects null components. */
    public OnDemandPrice {
        requireNonNull(location, "location");
        requireNonNull(variant, "variant");
        requireNonNull(since, "since");
    }
}
