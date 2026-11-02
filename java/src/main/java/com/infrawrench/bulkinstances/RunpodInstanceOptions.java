package com.infrawrench.bulkinstances;

/**
 * Options for {@link BulkInstances#fetchRunpodInstance(String, RunpodInstanceOptions)}: the same as for
 * {@link BulkInstances#fetchAwsInstance(String, String, AWSInstanceOptions)}. Immutable; build one with
 * {@link #builder()}.
 */
public final class RunpodInstanceOptions extends AWSInstanceOptions {
    private RunpodInstanceOptions(Builder b) {
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

    /** Builds {@link RunpodInstanceOptions}. Every option is optional; passing {@code null} restores its default. */
    public static final class Builder extends AWSInstanceOptions.Builder {
        private Builder() {}

        @Override
        public Builder token(String token) {
            super.token(token);
            return this;
        }

        @Override
        public Builder baseUrl(String baseUrl) {
            super.baseUrl(baseUrl);
            return this;
        }

        @Override
        public RunpodInstanceOptions build() {
            return new RunpodInstanceOptions(this);
        }
    }
}
