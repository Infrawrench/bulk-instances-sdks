package com.infrawrench.bulkinstances;

import java.io.IOException;
import java.util.OptionalInt;

/** Thrown when the pricing data cannot be downloaded. {@link #status()} is the HTTP status, if there was a response. */
public final class AWSPricingDataException extends IOException {
    private static final long serialVersionUID = 1L;

    /** The HTTP status, or 0 if there was no response. */
    private final int status;

    /**
     * An error without an HTTP response.
     *
     * @param message the detail message
     */
    public AWSPricingDataException(String message) {
        this(message, null);
    }

    /**
     * An error without an HTTP response, caused by {@code cause}.
     *
     * @param message the detail message
     * @param cause the underlying failure, e.g. the connection error
     */
    public AWSPricingDataException(String message, Throwable cause) {
        super(message, cause);
        this.status = 0;
    }

    /**
     * An error answered with an HTTP status.
     *
     * @param message the detail message
     * @param status the HTTP status
     */
    public AWSPricingDataException(String message, int status) {
        super(message);
        this.status = status;
    }

    /**
     * The HTTP status, if there was a response.
     *
     * @return the status, or empty if the request never got a response
     */
    public OptionalInt status() {
        return status == 0 ? OptionalInt.empty() : OptionalInt.of(status);
    }
}
