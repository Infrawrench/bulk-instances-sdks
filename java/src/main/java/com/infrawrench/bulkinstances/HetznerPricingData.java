package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * Hetzner's cloud server pricing data, keyed by server type ({@code cx23}). It has the same members as
 * {@link AWSPricingData} and decodes the same way; see the README for what Hetzner's data holds.
 */
public final class HetznerPricingData extends PricingData<HetznerInstance> {
    HetznerPricingData(Bundle b) {
        super(b);
    }

    @Override
    HetznerInstance newInstance(String name, RawInstance raw) {
        return new HetznerInstance(name, raw, this);
    }

    /**
     * The server type with this name, or empty if the bundle has never listed it.
     *
     * @param serverType e.g. {@code cx23}
     * @return the server type, the same object on every call
     */
    @Override
    public Optional<HetznerInstance> get(String serverType) {
        return super.get(serverType);
    }
}
