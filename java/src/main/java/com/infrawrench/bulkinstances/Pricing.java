package com.infrawrench.bulkinstances;

import java.util.List;

/**
 * The current price of everything still offered.
 *
 * @param onDemand the current on-demand prices (unmodifiable)
 * @param reserved the current reserved prices (unmodifiable)
 */
public record Pricing(List<OnDemandPrice> onDemand, List<ReservedPrice> reserved) {
    /** Keeps unmodifiable copies of the lists. */
    public Pricing {
        onDemand = List.copyOf(onDemand);
        reserved = List.copyOf(reserved);
    }
}
