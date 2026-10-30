package com.infrawrench.bulkinstances;

import static java.util.Objects.requireNonNull;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalDouble;
import java.util.function.DoubleFunction;

/** One instance type. Each getter decodes on first access and caches the result. */
public final class AWSInstance {
    private final String name;
    private final RawInstance raw;
    private final AWSPricingData data;
    private volatile Map<String, String> attributes;
    private volatile List<AttributeChange> attributesHistory;
    private volatile Pricing pricing;
    private volatile PricingHistory pricingHistory;

    AWSInstance(String name, RawInstance raw, AWSPricingData data) {
        this.name = name;
        this.raw = raw;
        this.data = data;
    }

    /**
     * The instance type, e.g. {@code m5.large}.
     *
     * @return the instance type
     */
    public String name() {
        return name;
    }

    /**
     * The publication date of the first price list that listed this instance.
     *
     * @return the creation date
     */
    public Instant createdAt() {
        return AWSPricingData.date(raw.createdAt());
    }

    /**
     * The publication date of the first price list that stopped listing it, or empty if AWS still lists it.
     *
     * @return the deletion date
     */
    public Optional<Instant> deletedAt() {
        return Double.isNaN(raw.deletedAt()) ? Optional.empty() : Optional.of(AWSPricingData.date(raw.deletedAt()));
    }

    /**
     * The latest attributes shared by every region. Regional differences are in {@link #attributesIn}.
     *
     * @return the attributes (unmodifiable)
     */
    public Map<String, String> attributes() {
        Map<String, String> out = attributes;
        if (out == null) {
            Map<String, String> m = new LinkedHashMap<>();
            for (AttributeChange c : attributesHistory()) {
                if (c.region().isPresent()) continue;
                if (c.value().isEmpty()) m.remove(c.key());
                else m.put(c.key(), c.value().get());
            }
            attributes = out = Collections.unmodifiableMap(m);
        }
        return out;
    }

    /**
     * The latest attributes in one AWS location (e.g. {@code US East (N. Virginia)}): the global ones with that
     * region's overrides on top. A regional override keeps applying even after a newer global change to the same
     * key.
     *
     * @param region the AWS location name
     * @return a new unmodifiable map
     */
    public Map<String, String> attributesIn(String region) {
        requireNonNull(region, "region");
        Map<String, String> out = new LinkedHashMap<>(attributes());
        Map<String, Optional<String>> overrides = new LinkedHashMap<>();
        for (AttributeChange c : attributesHistory()) {
            if (c.region().filter(region::equals).isPresent()) overrides.put(c.key(), c.value());
        }
        for (Map.Entry<String, Optional<String>> o : overrides.entrySet()) {
            if (o.getValue().isEmpty()) out.remove(o.getKey());
            else out.put(o.getKey(), o.getValue().get());
        }
        return Collections.unmodifiableMap(out);
    }

    /**
     * Every attribute change, oldest first, starting with the attributes the instance was first listed with.
     *
     * @return the changes (unmodifiable)
     */
    public List<AttributeChange> attributesHistory() {
        List<AttributeChange> out = attributesHistory;
        if (out == null) {
            AWSPricingData d = data;
            Instant created = createdAt();
            List<AttributeChange> l = new ArrayList<>();
            Rows a = raw.attrs();
            for (int r = 0; r < a.size(); r++) {
                l.add(new AttributeChange(created, d.str(a.get(r, 0)), Optional.of(d.str(a.get(r, 1))), Optional.empty()));
            }
            List<AttributeChange> changes = new ArrayList<>();
            Rows c = raw.attrChanges();
            for (int r = 0; r < c.size(); r++) {
                double value = c.get(r, 2), region = c.get(r, 3);
                changes.add(new AttributeChange(
                        AWSPricingData.date(c.get(r, 0)),
                        d.str(c.get(r, 1)),
                        Double.isNaN(value) ? Optional.empty() : Optional.of(d.str(value)),
                        Double.isNaN(region) ? Optional.empty() : Optional.of(d.str(region))));
            }
            // Stable, so rows with the same timestamp keep their order (later rows win).
            changes.sort(Comparator.comparing(AttributeChange::at));
            l.addAll(changes);
            attributesHistory = out = List.copyOf(l);
        }
        return out;
    }

    /**
     * The current price of everything still offered.
     *
     * @return the current prices
     */
    public Pricing pricing() {
        Pricing out = pricing;
        if (out == null) {
            PricingHistory h = pricingHistory();
            Map<Key, OnDemandPriceChange> od = new LinkedHashMap<>();
            for (OnDemandPriceChange r : h.onDemand()) od.put(new Key(r.location().region(), r.variant(), null), r);
            Map<Key, ReservedPriceChange> rs = new LinkedHashMap<>();
            for (ReservedPriceChange r : h.reserved()) rs.put(new Key(r.location().region(), r.variant(), r.term()), r);

            pricing = out = new Pricing(
                    od.values().stream()
                            .filter(r -> r.hourly().isPresent())
                            .map(r -> new OnDemandPrice(r.location(), r.variant(), r.hourly().getAsDouble(), r.at()))
                            .toList(),
                    rs.values().stream()
                            .filter(r -> r.hourly().isPresent())
                            .map(r -> new ReservedPrice(
                                    r.location(), r.variant(), r.term(), r.hourly().getAsDouble(),
                                    r.upfront().orElse(0), r.at()))
                            .toList());
        }
        return out;
    }

    /**
     * Every on-demand and reserved price change, oldest first.
     *
     * @return the changes
     */
    public PricingHistory pricingHistory() {
        PricingHistory out = pricingHistory;
        if (out == null) {
            AWSPricingData d = data;
            double base = raw.basePrice();
            // Rows repeat a few dozen locations; share one record per location.
            Map<Double, Location> locations = new HashMap<>();
            DoubleFunction<Location> location = i -> locations.computeIfAbsent(i, d::location);
            // [ts, region, variant, price: omitted = base price, null = no longer offered]
            List<OnDemandPriceChange> onDemand = new ArrayList<>();
            Rows o = raw.onDemand();
            for (int r = 0; r < o.size(); r++) {
                onDemand.add(new OnDemandPriceChange(
                        location.apply(o.get(r, 1)),
                        d.variant(o.get(r, 2)),
                        AWSPricingData.date(o.get(r, 0)),
                        price(o.length(r) <= 3 ? base : o.get(r, 3))));
            }
            // [ts, region, variant, term, hourly: null = no longer offered, upfront: omitted if 0]
            List<ReservedPriceChange> reserved = new ArrayList<>();
            Rows v = raw.reserved();
            for (int r = 0; r < v.size(); r++) {
                double hourly = v.get(r, 4), upfront = v.get(r, 5);
                boolean removed = Double.isNaN(hourly);
                reserved.add(new ReservedPriceChange(
                        location.apply(v.get(r, 1)),
                        d.variant(v.get(r, 2)),
                        d.term(v.get(r, 3)),
                        AWSPricingData.date(v.get(r, 0)),
                        price(hourly),
                        removed ? OptionalDouble.empty() : OptionalDouble.of(Double.isNaN(upfront) ? 0 : upfront)));
            }
            onDemand.sort(Comparator.comparing(OnDemandPriceChange::at));
            reserved.sort(Comparator.comparing(ReservedPriceChange::at));
            pricingHistory = out = new PricingHistory(onDemand, reserved);
        }
        return out;
    }

    private static OptionalDouble price(double p) {
        return Double.isNaN(p) ? OptionalDouble.empty() : OptionalDouble.of(p);
    }

    /**
     * What identifies a price: the region and variant, plus the term for reserved prices. Variants are equal when
     * all their fields are, so RDS's Single-AZ and Multi-AZ prices stay apart.
     */
    private record Key(String region, Variant variant, ReservedTerm term) {}
}
