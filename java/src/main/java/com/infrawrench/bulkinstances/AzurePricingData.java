package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * Azure's virtual machine pricing data, keyed by VM size ({@code Standard_D2s_v3}). It has the same members as
 * {@link AWSPricingData} and decodes the same way; see the README for what Azure's data holds.
 */
public final class AzurePricingData extends PricingData<AzureInstance> {
    AzurePricingData(Bundle b) {
        super(b);
    }

    @Override
    AzureInstance newInstance(String name, RawInstance raw) {
        return new AzureInstance(name, raw, this);
    }

    /**
     * The VM size with this name, or empty if the bundle has never listed it.
     *
     * @param size e.g. {@code Standard_D2s_v3}
     * @return the VM size, the same object on every call
     */
    @Override
    public Optional<AzureInstance> get(String size) {
        return super.get(size);
    }
}
