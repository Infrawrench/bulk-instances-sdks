package com.infrawrench.bulkinstances;

/** One Google Cloud Compute Engine machine type. It has the same members as {@link AWSInstance}, which it extends. */
public final class GCPInstance extends AWSInstance {
    GCPInstance(String name, RawInstance raw, GCPPricingData data) {
        super(name, raw, data);
    }
}
