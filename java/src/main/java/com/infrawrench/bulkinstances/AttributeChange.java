package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

import java.time.Instant;
import java.util.Optional;

/**
 * One attribute change.
 *
 * @param at when the change took effect
 * @param key the attribute name, e.g. {@code vcpu}
 * @param value the new value. Empty means the attribute was removed.
 * @param region the AWS location this change applies to, or empty for every region.
 */
public record AttributeChange(Instant at, String key, Optional<String> value, Optional<String> region) {
    /** Rejects null components. */
    public AttributeChange {
        requireNonNull(at, "at");
        requireNonNull(key, "key");
        requireNonNull(value, "value");
        requireNonNull(region, "region");
    }
}
