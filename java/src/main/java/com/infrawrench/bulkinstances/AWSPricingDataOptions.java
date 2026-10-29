package com.infrawrench.bulkinstances;

import java.io.File;
import java.nio.file.Path;
import java.util.Optional;

/**
 * Options for {@link BulkInstances#downloadAwsEc2PricingData(AWSPricingDataOptions)}. Immutable; build one with
 * {@link #builder()}.
 */
public final class AWSPricingDataOptions {
    static final String DEFAULT_BASE_URL = "https://instances-bundles.infrawrench.com";

    private final String token;
    private final boolean cachePricingData;
    private final Path cachePath;
    private final String baseUrl;

    private AWSPricingDataOptions(Builder b) {
        this.token = b.token;
        this.cachePricingData = b.cachePricingData;
        this.cachePath = b.cachePath != null ? b.cachePath : defaultCachePath();
        this.baseUrl = b.baseUrl != null ? b.baseUrl : DEFAULT_BASE_URL;
    }

    /**
     * Starts a builder with every option at its default.
     *
     * @return a new builder
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Your Infrawrench API token, if one was given. When empty, the {@code INFRAWRENCH_API_KEY} environment
     * variable is used.
     *
     * @return the token
     */
    public Optional<String> token() {
        return Optional.ofNullable(token);
    }

    /**
     * Whether to cache the pricing data. Defaults to true.
     *
     * @return whether to cache
     */
    public boolean cachePricingData() {
        return cachePricingData;
    }

    /**
     * The cache path. Defaults to {@code ~/.infrawrench/aws_pricing_data}
     *
     * @return the cache directory
     */
    public Path cachePath() {
        return cachePath;
    }

    /**
     * Where the bundles are served from. Defaults to {@code https://instances-bundles.infrawrench.com}
     *
     * @return the base URL
     */
    public String baseUrl() {
        return baseUrl;
    }

    /** {@code ~/.infrawrench/aws_pricing_data}, with the home directory found the way Node's {@code os.homedir()} does. */
    private static Path defaultCachePath() {
        String home = File.separatorChar == '/' ? System.getenv("HOME") : null;
        if (home == null || home.isEmpty()) home = System.getProperty("user.home");
        return Path.of(home, ".infrawrench", "aws_pricing_data");
    }

    /** Builds {@link AWSPricingDataOptions}. Every option is optional; passing {@code null} restores its default. */
    public static final class Builder {
        private String token;
        private boolean cachePricingData = true;
        private Path cachePath;
        private String baseUrl;

        private Builder() {}

        /**
         * Defines your Infrawrench API token. Defaults to the {@code INFRAWRENCH_API_KEY} environment variable.
         *
         * @param token any Infrawrench bearer credential
         * @return this builder
         */
        public Builder token(String token) {
            this.token = token;
            return this;
        }

        /**
         * Whether to cache the pricing data. Defaults to true.
         *
         * @param cachePricingData false to always download and never touch the disk
         * @return this builder
         */
        public Builder cachePricingData(boolean cachePricingData) {
            this.cachePricingData = cachePricingData;
            return this;
        }

        /**
         * The cache path. Defaults to {@code ~/.infrawrench/aws_pricing_data}
         *
         * @param cachePath the cache directory
         * @return this builder
         */
        public Builder cachePath(Path cachePath) {
            this.cachePath = cachePath;
            return this;
        }

        /**
         * Where the bundles are served from. Defaults to {@code https://instances-bundles.infrawrench.com}
         *
         * @param baseUrl the base URL; trailing slashes are ignored
         * @return this builder
         */
        public Builder baseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
            return this;
        }

        /**
         * Builds the options.
         *
         * @return the options
         */
        public AWSPricingDataOptions build() {
            return new AWSPricingDataOptions(this);
        }
    }
}
