package com.infrawrench.bulkinstances;

/** One IBM Cloud Virtual Server for VPC profile. It has the same members as {@link AWSInstance}, which it extends. */
public final class IBMInstance extends AWSInstance {
    IBMInstance(String name, RawInstance raw, IBMPricingData data) {
        super(name, raw, data);
    }
}
