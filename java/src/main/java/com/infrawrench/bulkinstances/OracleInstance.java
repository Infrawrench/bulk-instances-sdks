package com.infrawrench.bulkinstances;

/** One Oracle Cloud compute shape. It has the same members as {@link AWSInstance}, which it extends. */
public final class OracleInstance extends AWSInstance {
    OracleInstance(String name, RawInstance raw, OraclePricingData data) {
        super(name, raw, data);
    }
}
