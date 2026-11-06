package com.infrawrench.bulkinstances;

/** One OVHcloud eco dedicated server. It has the same members as {@link AWSInstance}, which it extends. */
public final class OVHEcoInstance extends AWSInstance {
    OVHEcoInstance(String name, RawInstance raw, OVHEcoPricingData data) {
        super(name, raw, data);
    }
}
