package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

/**
 * The product fields that pick a price.
 *
 * @param operatingSystem e.g. {@code Linux}
 * @param tenancy e.g. {@code Shared}
 * @param licenseModel e.g. {@code No License required}
 * @param preInstalledSw e.g. {@code NA}
 * @param capacitystatus e.g. {@code Used}
 */
public record Variant(
        String operatingSystem, String tenancy, String licenseModel, String preInstalledSw, String capacitystatus) {
    /** Rejects null components. */
    public Variant {
        requireNonNull(operatingSystem, "operatingSystem");
        requireNonNull(tenancy, "tenancy");
        requireNonNull(licenseModel, "licenseModel");
        requireNonNull(preInstalledSw, "preInstalledSw");
        requireNonNull(capacitystatus, "capacitystatus");
    }
}
