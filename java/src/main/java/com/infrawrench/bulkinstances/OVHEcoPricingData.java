package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * OVHcloud's eco dedicated server pricing data, keyed by server ({@code 24sys01}). It has the same members as
 * {@link AWSPricingData} and decodes the same way; see the README for what OVHcloud's data holds.
 */
public final class OVHEcoPricingData extends PricingData<OVHEcoInstance> {
    OVHEcoPricingData(Bundle b) {
        super(b);
    }

    @Override
    OVHEcoInstance newInstance(String name, RawInstance raw) {
        return new OVHEcoInstance(name, raw, this);
    }

    /**
     * The server with this name, or empty if the bundle has never listed it.
     *
     * @param server e.g. {@code 24sys01}
     * @return the server, the same object on every call
     */
    @Override
    public Optional<OVHEcoInstance> get(String server) {
        return super.get(server);
    }
}
