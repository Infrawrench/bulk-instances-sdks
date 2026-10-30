package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The product fields that pick a price.
 *
 * <p>{@code fields} holds all of them. The other components are EC2's variant fields: on other platforms they are
 * {@code ""} unless the platform has a field with that name (RDS has {@code licenseModel}).
 *
 * @param fields every field that picks the price, keyed by name, in {@link AWSPricingData#variantKeys()} order: for
 *     RDS, {@code databaseEngine}, {@code deploymentOption} and so on
 * @param operatingSystem e.g. {@code Linux}
 * @param tenancy e.g. {@code Shared}
 * @param licenseModel e.g. {@code No License required}
 * @param preInstalledSw e.g. {@code NA}
 * @param capacitystatus e.g. {@code Used}
 */
public record Variant(
        Map<String, String> fields, String operatingSystem, String tenancy, String licenseModel,
        String preInstalledSw, String capacitystatus) {
    /** Rejects null components and keeps an unmodifiable copy of {@code fields}, in its iteration order. */
    public Variant {
        requireNonNull(fields, "fields");
        requireNonNull(operatingSystem, "operatingSystem");
        requireNonNull(tenancy, "tenancy");
        requireNonNull(licenseModel, "licenseModel");
        requireNonNull(preInstalledSw, "preInstalledSw");
        requireNonNull(capacitystatus, "capacitystatus");
        Map<String, String> copy = new LinkedHashMap<>();
        fields.forEach((k, v) -> copy.put(requireNonNull(k, "fields key"), requireNonNull(v, "fields value")));
        fields = Collections.unmodifiableMap(copy);
    }

    /**
     * An EC2 variant, whose {@code fields} are these five under {@link BulkInstances#EC2_VARIANT_KEYS}.
     *
     * @param operatingSystem e.g. {@code Linux}
     * @param tenancy e.g. {@code Shared}
     * @param licenseModel e.g. {@code No License required}
     * @param preInstalledSw e.g. {@code NA}
     * @param capacitystatus e.g. {@code Used}
     */
    public Variant(
            String operatingSystem, String tenancy, String licenseModel, String preInstalledSw, String capacitystatus) {
        this(ec2(operatingSystem, tenancy, licenseModel, preInstalledSw, capacitystatus),
                operatingSystem, tenancy, licenseModel, preInstalledSw, capacitystatus);
    }

    private static Map<String, String> ec2(String... values) {
        List<String> keys = BulkInstances.EC2_VARIANT_KEYS;
        Map<String, String> out = new LinkedHashMap<>();
        for (int i = 0; i < keys.size(); i++) out.put(keys.get(i), requireNonNull(values[i], keys.get(i)));
        return out;
    }
}
