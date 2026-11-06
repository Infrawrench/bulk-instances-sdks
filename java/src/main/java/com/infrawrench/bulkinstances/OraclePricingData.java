package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * Oracle Cloud's compute pricing data, keyed by shape ({@code VM.Standard.E5.Flex-2-16}). It has the same members as
 * {@link AWSPricingData} and decodes the same way; see the README for what Oracle Cloud's data holds.
 */
public final class OraclePricingData extends PricingData<OracleInstance> {
    OraclePricingData(Bundle b) {
        super(b);
    }

    @Override
    OracleInstance newInstance(String name, RawInstance raw) {
        return new OracleInstance(name, raw, this);
    }

    /**
     * The shape with this name, or empty if the bundle has never listed it.
     *
     * @param shape e.g. {@code VM.Standard.E5.Flex-2-16}
     * @return the shape, the same object on every call
     */
    @Override
    public Optional<OracleInstance> get(String shape) {
        return super.get(shape);
    }
}
