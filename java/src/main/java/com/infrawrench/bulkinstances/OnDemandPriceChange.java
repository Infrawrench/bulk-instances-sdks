package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

import java.time.Instant;
import java.util.OptionalDouble;

/**
 * One on-demand price change.
 *
 * @param location where the price applies
 * @param variant the product fields that pick the price
 * @param at when the change took effect
 * @param hourly USD per hour. Empty means no longer offered from {@code at} on.
 */
public record OnDemandPriceChange(Location location, Variant variant, Instant at, OptionalDouble hourly) {
    /** Rejects null components. */
    public OnDemandPriceChange {
        requireNonNull(location, "location");
        requireNonNull(variant, "variant");
        requireNonNull(at, "at");
        requireNonNull(hourly, "hourly");
    }
}
