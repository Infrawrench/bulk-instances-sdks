package com.infrawrench.bulkinstances;

/** One Azure virtual machine size. It has the same members as {@link AWSInstance}, which it extends. */
public final class AzureInstance extends AWSInstance {
    AzureInstance(String name, RawInstance raw, AzurePricingData data) {
        super(name, raw, data);
    }
}
