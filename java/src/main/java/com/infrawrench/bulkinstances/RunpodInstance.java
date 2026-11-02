package com.infrawrench.bulkinstances;

/** One RunPod GPU type or CPU pod. It has the same members as {@link AWSInstance}, which it extends. */
public final class RunpodInstance extends AWSInstance {
    RunpodInstance(String name, RawInstance raw, RunpodPricingData data) {
        super(name, raw, data);
    }
}
