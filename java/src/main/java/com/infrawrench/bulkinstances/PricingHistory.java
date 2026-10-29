package com.infrawrench.bulkinstances;

import java.util.List;

/**
 * Every on-demand and reserved price change.
 *
 * @param onDemand oldest first (unmodifiable).
 * @param reserved oldest first (unmodifiable).
 */
public record PricingHistory(List<OnDemandPriceChange> onDemand, List<ReservedPriceChange> reserved) {
    /** Keeps unmodifiable copies of the lists. */
    public PricingHistory {
        onDemand = List.copyOf(onDemand);
        reserved = List.copyOf(reserved);
    }
}
