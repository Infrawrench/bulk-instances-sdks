package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * One AWS platform's pricing data, keyed by instance type.
 *
 * <p>Nothing is decoded until it is asked for: {@link #get} wraps the raw rows, and each getter on the returned
 * {@link AWSInstance} decodes its part on first access and keeps the result. Everything returned is immutable and
 * shared between calls, so the data is safe to use from several threads.
 */
public final class AWSPricingData extends PricingData<AWSInstance> {
    AWSPricingData(Bundle b) {
        super(b);
    }

    @Override
    AWSInstance newInstance(String name, RawInstance raw) {
        return new AWSInstance(name, raw, this);
    }

    /**
     * The instance with this type (e.g. {@code m5.large}), or empty if the bundle has never listed it.
     *
     * @param instanceType e.g. {@code m5.large}
     * @return the instance, the same object on every call
     */
    @Override
    public Optional<AWSInstance> get(String instanceType) {
        return super.get(instanceType);
    }
}
