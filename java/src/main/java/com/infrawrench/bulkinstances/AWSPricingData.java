package com.infrawrench.bulkinstances;

import com.infrawrench.bulkinstances.BundleParser.RawRegion;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The AWS EC2 pricing data, keyed by instance type.
 *
 * <p>Nothing is decoded until it is asked for: {@link #get} wraps the raw rows, and each getter on the returned
 * {@link AWSInstance} decodes its part on first access and keeps the result. Everything returned is immutable and
 * shared between calls, so the data is safe to use from several threads.
 */
public final class AWSPricingData {
    private final String[] table;
    private final double[] snapshots;
    private final List<RawRegion> rawRegions;
    private final Rows rawVariants;
    private final Rows rawTerms;
    private final Map<String, RawInstance> raw;
    private final List<String> keys;
    private final Map<String, AWSInstance> instances = new ConcurrentHashMap<>();
    private volatile List<Variant> variants;
    private volatile List<ReservedTerm> terms;
    private volatile Map<String, Map<String, String>> regions;

    AWSPricingData(
            String[] table, double[] snapshots, List<RawRegion> regions, Rows variants, Rows terms,
            Map<String, RawInstance> instances) {
        this.table = table;
        this.snapshots = snapshots;
        this.rawRegions = regions;
        this.rawVariants = variants;
        this.rawTerms = terms;
        this.raw = instances;
        this.keys = List.copyOf(instances.keySet());
    }

    /**
     * Every instance type in the bundle, including ones AWS no longer lists (see {@link AWSInstance#deletedAt()}).
     *
     * @return the instance types, in bundle order (unmodifiable)
     */
    public List<String> keys() {
        return keys;
    }

    /**
     * Whether the bundle has ever listed this instance type.
     *
     * @param instanceType e.g. {@code m5.large}
     * @return whether {@link #get} finds it
     */
    public boolean has(String instanceType) {
        return raw.containsKey(instanceType);
    }

    /**
     * The instance with this type (e.g. {@code m5.large}), or empty if the bundle has never listed it.
     *
     * @param instanceType e.g. {@code m5.large}
     * @return the instance, the same object on every call
     */
    public Optional<AWSInstance> get(String instanceType) {
        RawInstance r = raw.get(instanceType);
        if (r == null) return Optional.empty();
        return Optional.of(instances.computeIfAbsent(instanceType, name -> new AWSInstance(name, r, this)));
    }

    /**
     * The publication date of every AWS price list in the bundle, oldest first.
     *
     * @return the publication dates (unmodifiable)
     */
    public List<Instant> snapshots() {
        return Arrays.stream(snapshots).mapToObj(AWSPricingData::date).toList();
    }

    /**
     * Attributes of each AWS location ({@code regionCode}, {@code locationType}), keyed by location name.
     *
     * @return the locations (unmodifiable, as are the attribute maps)
     */
    public Map<String, Map<String, String>> regions() {
        Map<String, Map<String, String>> out = regions;
        if (out == null) {
            Map<String, Map<String, String>> m = new LinkedHashMap<>();
            for (RawRegion r : rawRegions) {
                Map<String, String> attrs = new LinkedHashMap<>();
                for (int i = 0; i < r.pairs().size(); i++) attrs.put(str(r.pairs().get(i, 0)), str(r.pairs().get(i, 1)));
                m.put(str(r.location()), Collections.unmodifiableMap(attrs));
            }
            regions = out = Collections.unmodifiableMap(m);
        }
        return out;
    }

    static Instant date(double ts) {
        return Instant.ofEpochMilli((long) (ts * 1000));
    }

    /** The table index {@code i} holds, or -1 if it holds none. */
    private static int index(double i) {
        return i == (int) i ? (int) i : -1;
    }

    String str(double i) {
        int k = index(i);
        if (k < 0 || k >= table.length) {
            String shown = i == Math.rint(i) && !Double.isInfinite(i) ? Long.toString((long) i) : Double.toString(i);
            throw new IndexOutOfBoundsException("string index " + shown + " out of range");
        }
        return table[k];
    }

    Location location(double i) {
        String region = str(i);
        Map<String, String> attrs = regions().get(region);
        return new Location(region, Optional.ofNullable(attrs == null ? null : attrs.get("regionCode")));
    }

    Variant variant(double i) {
        List<Variant> out = variants;
        if (out == null) {
            List<Variant> l = new ArrayList<>();
            Rows v = rawVariants;
            for (int r = 0; r < v.size(); r++) {
                l.add(new Variant(str(v.get(r, 0)), str(v.get(r, 1)), str(v.get(r, 2)), str(v.get(r, 3)), str(v.get(r, 4))));
            }
            variants = out = List.copyOf(l);
        }
        return out.get(index(i));
    }

    ReservedTerm term(double i) {
        List<ReservedTerm> out = terms;
        if (out == null) {
            List<ReservedTerm> l = new ArrayList<>();
            Rows t = rawTerms;
            for (int r = 0; r < t.size(); r++) l.add(new ReservedTerm(str(t.get(r, 0)), str(t.get(r, 1)), str(t.get(r, 2))));
            terms = out = List.copyOf(l);
        }
        return out.get(index(i));
    }
}
