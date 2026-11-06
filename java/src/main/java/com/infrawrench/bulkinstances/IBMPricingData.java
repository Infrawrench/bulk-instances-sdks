package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * IBM Cloud's Virtual Server for VPC pricing data, keyed by profile ({@code bx3d-2x10}). It has the same members as
 * {@link AWSPricingData} and decodes the same way; see the README for what IBM Cloud's data holds.
 */
public final class IBMPricingData extends PricingData<IBMInstance> {
    IBMPricingData(Bundle b) {
        super(b);
    }

    @Override
    IBMInstance newInstance(String name, RawInstance raw) {
        return new IBMInstance(name, raw, this);
    }

    /**
     * The profile with this name, or empty if the bundle has never listed it.
     *
     * @param profile e.g. {@code bx3d-2x10}
     * @return the profile, the same object on every call
     */
    @Override
    public Optional<IBMInstance> get(String profile) {
        return super.get(profile);
    }
}
