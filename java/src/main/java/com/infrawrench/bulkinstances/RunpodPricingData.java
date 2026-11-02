package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.Bundle;
import java.util.Optional;

/**
 * RunPod's pricing data, keyed by GPU type id ({@code NVIDIA H100 80GB HBM3}) or CPU pod id ({@code cpu3c-2-4}).
 * It has the same members as {@link AWSPricingData} and decodes the same way; see the README for what RunPod's data
 * holds.
 */
public final class RunpodPricingData extends PricingData<RunpodInstance> {
    RunpodPricingData(Bundle b) {
        super(b);
    }

    @Override
    RunpodInstance newInstance(String name, RawInstance raw) {
        return new RunpodInstance(name, raw, this);
    }

    /**
     * The GPU type or CPU pod with this id, or empty if the bundle has never listed it.
     *
     * @param id e.g. {@code NVIDIA H100 80GB HBM3} or {@code cpu3c-2-4}
     * @return the GPU type or CPU pod, the same object on every call
     */
    @Override
    public Optional<RunpodInstance> get(String id) {
        return super.get(id);
    }
}
