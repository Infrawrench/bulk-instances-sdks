package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

import java.time.Instant;

/**
 * A current reserved price.
 *
 * @param location where the price applies
 * @param variant the product fields that pick the price
 * @param term the reservation terms
 * @param hourly USD per hour.
 * @param upfront USD paid up front.
 * @param since when this price took effect.
 */
public record ReservedPrice(
        Location location, Variant variant, ReservedTerm term, double hourly, double upfront, Instant since) {
    /** Rejects null components. */
    public ReservedPrice {
        requireNonNull(location, "location");
        requireNonNull(variant, "variant");
        requireNonNull(term, "term");
        requireNonNull(since, "since");
    }
}
