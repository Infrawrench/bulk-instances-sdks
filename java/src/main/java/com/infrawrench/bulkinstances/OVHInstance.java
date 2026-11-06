package com.infrawrench.bulkinstances;

/** One OVHcloud Public Cloud flavor. It has the same members as {@link AWSInstance}, which it extends. */
public final class OVHInstance extends AWSInstance {
    OVHInstance(String name, RawInstance raw, OVHPricingData data) {
        super(name, raw, data);
    }
}
