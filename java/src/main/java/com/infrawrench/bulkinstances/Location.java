package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

import java.util.Optional;

/**
 * An AWS location.
 *
 * @param region the AWS location name, e.g. {@code US East (N. Virginia)}
 * @param regionCode e.g. {@code us-east-1}. Empty for locations the price list never gave a code.
 */
public record Location(String region, Optional<String> regionCode) {
    /** Rejects null components. */
    public Location {
        requireNonNull(region, "region");
        requireNonNull(regionCode, "regionCode");
    }
}
