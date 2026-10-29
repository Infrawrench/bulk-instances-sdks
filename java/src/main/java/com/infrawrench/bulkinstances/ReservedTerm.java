package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

/**
 * The terms of a reserved price.
 *
 * @param leaseContractLength e.g. {@code 1yr}
 * @param offeringClass e.g. {@code standard}
 * @param purchaseOption e.g. {@code No Upfront}
 */
public record ReservedTerm(String leaseContractLength, String offeringClass, String purchaseOption) {
    /** Rejects null components. */
    public ReservedTerm {
        requireNonNull(leaseContractLength, "leaseContractLength");
        requireNonNull(offeringClass, "offeringClass");
        requireNonNull(purchaseOption, "purchaseOption");
    }
}
