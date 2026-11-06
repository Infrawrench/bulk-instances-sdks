package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * OVHcloud's Public Cloud pricing data, keyed by flavor ({@code b3-8}). It has the same members as
 * {@link AWSPricingData} and decodes the same way; see the README for what OVHcloud's data holds.
 */
public final class OVHPricingData extends PricingData<OVHInstance> {
    OVHPricingData(Bundle b) {
        super(b);
    }

    @Override
    OVHInstance newInstance(String name, RawInstance raw) {
        return new OVHInstance(name, raw, this);
    }

    /**
     * The flavor with this name, or empty if the bundle has never listed it.
     *
     * @param flavor e.g. {@code b3-8}
     * @return the flavor, the same object on every call
     */
    @Override
    public Optional<OVHInstance> get(String flavor) {
        return super.get(flavor);
    }
}
