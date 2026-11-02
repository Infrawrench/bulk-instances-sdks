package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * Alibaba Cloud's ECS pricing data, keyed by instance type ({@code ecs.g6.large}). It has the same members as
 * {@link AWSPricingData} and decodes the same way; see the README for what Alibaba's data holds.
 */
public final class AlibabaPricingData extends PricingData<AlibabaInstance> {
    AlibabaPricingData(Bundle b) {
        super(b);
    }

    @Override
    AlibabaInstance newInstance(String name, RawInstance raw) {
        return new AlibabaInstance(name, raw, this);
    }

    /**
     * The instance type with this name, or empty if the bundle has never listed it.
     *
     * @param instanceType e.g. {@code ecs.g6.large}
     * @return the instance type, the same object on every call
     */
    @Override
    public Optional<AlibabaInstance> get(String instanceType) {
        return super.get(instanceType);
    }
}
