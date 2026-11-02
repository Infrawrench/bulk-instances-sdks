package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * Google Cloud's Compute Engine pricing data, keyed by machine type ({@code n2-standard-2}). It has the same members as
 * {@link AWSPricingData} and decodes the same way; see the README for what Google Cloud's data holds.
 */
public final class GCPPricingData extends PricingData<GCPInstance> {
    GCPPricingData(Bundle b) {
        super(b);
    }

    @Override
    GCPInstance newInstance(String name, RawInstance raw) {
        return new GCPInstance(name, raw, this);
    }

    /**
     * The machine type with this name, or empty if the bundle has never listed it.
     *
     * @param machineType e.g. {@code n2-standard-2}
     * @return the machine type, the same object on every call
     */
    @Override
    public Optional<GCPInstance> get(String machineType) {
        return super.get(machineType);
    }
}
