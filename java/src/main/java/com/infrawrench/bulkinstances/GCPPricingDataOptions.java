package com.infrawrench.bulkinstances;

import java.nio.file.Path;

/**
 * Options for {@link BulkInstances#downloadGcpPricingData(GCPPricingDataOptions)}: the same as for the
 * AWS platforms. Immutable; build one with {@link #builder()}.
 */
public final class GCPPricingDataOptions extends AWSPricingDataOptions {
    private GCPPricingDataOptions(Builder b) {
        super(b);
    }

    /**
     * Starts a builder with every option at its default.
     *
     * @return a new builder
     */
    public static Builder builder() {
        return new Builder();
    }

    /** Builds {@link GCPPricingDataOptions}. Every option is optional; passing {@code null} restores its default. */
    public static final class Builder extends AWSPricingDataOptions.Builder {
        private Builder() {}

        @Override
        public Builder token(String token) {
            super.token(token);
            return this;
        }

        @Override
        public Builder cachePricingData(boolean cachePricingData) {
            super.cachePricingData(cachePricingData);
            return this;
        }

        @Override
        public Builder cachePath(Path cachePath) {
            super.cachePath(cachePath);
            return this;
        }

        @Override
        public Builder baseUrl(String baseUrl) {
            super.baseUrl(baseUrl);
            return this;
        }

        @Override
        public GCPPricingDataOptions build() {
            return new GCPPricingDataOptions(this);
        }
    }
}
