package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

import java.time.Instant;
import java.util.OptionalDouble;

/**
 * One reserved price change.
 *
 * @param location where the price applies
 * @param variant the product fields that pick the price
 * @param term the reservation terms
 * @param at when the change took effect
 * @param hourly USD per hour. Empty means no longer offered from {@code at} on.
 * @param upfront USD paid up front. Empty when {@code hourly} is.
 */
public record ReservedPriceChange(
        Location location, Variant variant, ReservedTerm term, Instant at, OptionalDouble hourly,
        OptionalDouble upfront) {
    /** Rejects null components. */
    public ReservedPriceChange {
        requireNonNull(location, "location");
        requireNonNull(variant, "variant");
        requireNonNull(term, "term");
        requireNonNull(at, "at");
        requireNonNull(hourly, "hourly");
        requireNonNull(upfront, "upfront");
    }
}
