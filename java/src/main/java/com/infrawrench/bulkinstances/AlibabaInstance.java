package com.infrawrench.bulkinstances;

/** One Alibaba Cloud ECS instance type. It has the same members as {@link AWSInstance}, which it extends. */
public final class AlibabaInstance extends AWSInstance {
    AlibabaInstance(String name, RawInstance raw, AlibabaPricingData data) {
        super(name, raw, data);
    }
}
