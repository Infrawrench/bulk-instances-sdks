package com.infrawrench.bulkinstances;

import java.util.Optional;

/**
 * Options for {@link BulkInstances#fetchAwsInstance(String, String, AWSInstanceOptions)}. Immutable; build one with
 * {@link #builder()}.
 */
public final class AWSInstanceOptions {
    static final String DEFAULT_BASE_URL = "https://app.infrawrench.com";

    private final String token;
    private final String baseUrl;

    private AWSInstanceOptions(Builder b) {
        this.token = b.token;
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
     * Where the Infrawrench API is served from. Defaults to {@code https://app.infrawrench.com}
     *
     * @return the base URL
     */
    public String baseUrl() {
        return baseUrl;
    }

    /** Builds {@link AWSInstanceOptions}. Every option is optional; passing {@code null} restores its default. */
    public static final class Builder {
        private String token;
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
         * Where the Infrawrench API is served from. Defaults to {@code https://app.infrawrench.com}
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
        public AWSInstanceOptions build() {
            return new AWSInstanceOptions(this);
        }
    }
}
