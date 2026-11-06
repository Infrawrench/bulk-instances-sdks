package com.infrawrench.bulkinstances;

/** One Hetzner cloud server type. It has the same members as {@link AWSInstance}, which it extends. */
public final class HetznerInstance extends AWSInstance {
    HetznerInstance(String name, RawInstance raw, HetznerPricingData data) {
        super(name, raw, data);
    }
}
