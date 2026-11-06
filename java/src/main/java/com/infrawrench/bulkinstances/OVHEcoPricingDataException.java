package com.infrawrench.bulkinstances;

/**
 * Thrown when OVHcloud's eco dedicated server pricing data cannot be downloaded. {@link #status()} is the HTTP
 * status, if there was a
 * response.
 */
public final class OVHEcoPricingDataException extends AWSPricingDataException {
    private static final long serialVersionUID = 1L;

    /**
     * An error without an HTTP response.
     *
     * @param message the detail message
     */
    public OVHEcoPricingDataException(String message) {
        super(message, 0, null);
    }

    /**
     * An error without an HTTP response, caused by {@code cause}.
     *
     * @param message the detail message
     * @param cause the underlying failure, e.g. the connection error
     */
    public OVHEcoPricingDataException(String message, Throwable cause) {
        super(message, 0, cause);
    }

    /**
     * An error answered with an HTTP status.
     *
     * @param message the detail message
     * @param status the HTTP status
     */
    public OVHEcoPricingDataException(String message, int status) {
        super(message, status, null);
    }

    /** The same failure as {@code e}: its message, status and cause. */
    OVHEcoPricingDataException(AWSPricingDataException e) {
        super(e.getMessage(), e.status().orElse(0), e.getCause());
    }
}
