import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonGenerator;
import com.infrawrench.bulkinstances.AWSInstance;
import com.infrawrench.bulkinstances.AlibabaInstance;
import com.infrawrench.bulkinstances.AlibabaInstanceOptions;
import com.infrawrench.bulkinstances.AlibabaPricingData;
import com.infrawrench.bulkinstances.AlibabaPricingDataException;
import com.infrawrench.bulkinstances.AlibabaPricingDataOptions;
import com.infrawrench.bulkinstances.AWSInstanceOptions;
import com.infrawrench.bulkinstances.AWSPricingData;
import com.infrawrench.bulkinstances.AWSPricingDataException;
import com.infrawrench.bulkinstances.AWSPricingDataOptions;
import com.infrawrench.bulkinstances.AttributeChange;
import com.infrawrench.bulkinstances.AzureInstance;
import com.infrawrench.bulkinstances.AzurePricingData;
import com.infrawrench.bulkinstances.AzurePricingDataException;
import com.infrawrench.bulkinstances.AzurePricingDataOptions;
import com.infrawrench.bulkinstances.BulkInstances;
import com.infrawrench.bulkinstances.GCPInstance;
import com.infrawrench.bulkinstances.GCPPricingData;
import com.infrawrench.bulkinstances.GCPPricingDataException;
import com.infrawrench.bulkinstances.GCPPricingDataOptions;
import com.infrawrench.bulkinstances.Location;
import com.infrawrench.bulkinstances.OnDemandPrice;
import com.infrawrench.bulkinstances.OnDemandPriceChange;
import com.infrawrench.bulkinstances.PricingData;
import com.infrawrench.bulkinstances.ReservedPrice;
import com.infrawrench.bulkinstances.ReservedPriceChange;
import com.infrawrench.bulkinstances.ReservedTerm;
import com.infrawrench.bulkinstances.RunpodInstance;
import com.infrawrench.bulkinstances.RunpodInstanceOptions;
import com.infrawrench.bulkinstances.RunpodPricingData;
import com.infrawrench.bulkinstances.RunpodPricingDataException;
import com.infrawrench.bulkinstances.RunpodPricingDataOptions;
import com.infrawrench.bulkinstances.Variant;
import java.io.IOException;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalDouble;
import java.util.TreeSet;

public final class Dump {
    public static void main(String[] args) throws IOException {
        String baseUrl = args[0], cachePath = args[1], token = args[2], cache = args[3];
        String platform = args.length > 4 ? args[4] : null;
        String instanceType = args.length > 5 ? args[5] : null;
        JsonGenerator g = new JsonFactory().createGenerator(System.out);

        if (instanceType != null) {
            Optional<? extends AWSInstance> i;
            try {
                // RunPod and Alibaba have their own functions, returning their own types and exceptions.
                if ("runpod".equals(platform)) {
                    Optional<RunpodInstance> r;
                    try {
                        r = BulkInstances.fetchRunpodInstance(instanceType,
                                instanceOptions(RunpodInstanceOptions.builder(), baseUrl, token).build());
                    } catch (AWSPricingDataException e) {
                        throw providerException(e, RunpodPricingDataException.class);
                    }
                    expectInstance(r, RunpodInstance.class);
                    i = r;
                } else if ("alibaba".equals(platform)) {
                    Optional<AlibabaInstance> a;
                    try {
                        a = BulkInstances.fetchAlibabaInstance(instanceType,
                                instanceOptions(AlibabaInstanceOptions.builder(), baseUrl, token).build());
                    } catch (AWSPricingDataException e) {
                        throw providerException(e, AlibabaPricingDataException.class);
                    }
                    expectInstance(a, AlibabaInstance.class);
                    i = a;
                } else {
                    i = BulkInstances.fetchAwsInstance(
                            platform, instanceType, instanceOptions(AWSInstanceOptions.builder(), baseUrl, token).build());
                }
            } catch (AWSPricingDataException e) {
                error(g, e);
                return;
            }
            g.writeStartObject();
            g.writeFieldName("instance");
            if (i.isPresent()) {
                // The regions its attributes are overridden in; every other one is the same as `attributes`.
                TreeSet<String> regions = new TreeSet<>();
                for (AttributeChange c : i.get().attributesHistory()) c.region().ifPresent(regions::add);
                List<String> locations = new ArrayList<>(regions);
                locations.add("Mystery");
                locations.add("Nowhere");
                instance(g, i.get(), locations);
            } else {
                g.writeNull();
            }
            g.writeEndObject();
            g.flush();
            System.out.println();
            return;
        }

        PricingData<?> data;
        try {
            // RunPod, Alibaba, Azure and GCP have their own functions and types, and their own exceptions.
            if ("runpod".equals(platform)) {
                RunpodPricingData d;
                try {
                    d = BulkInstances.downloadRunpodPricingData(
                            options(RunpodPricingDataOptions.builder(), baseUrl, cachePath, token, cache).build());
                } catch (AWSPricingDataException e) {
                    throw providerException(e, RunpodPricingDataException.class);
                }
                RunpodInstance first = d.keys().isEmpty() ? null : d.get(d.keys().get(0)).orElseThrow();
                expectTypes(d, first, RunpodPricingData.class, RunpodInstance.class);
                data = d;
            } else if ("alibaba".equals(platform)) {
                AlibabaPricingData d;
                try {
                    d = BulkInstances.downloadAlibabaPricingData(
                            options(AlibabaPricingDataOptions.builder(), baseUrl, cachePath, token, cache).build());
                } catch (AWSPricingDataException e) {
                    throw providerException(e, AlibabaPricingDataException.class);
                }
                AlibabaInstance first = d.keys().isEmpty() ? null : d.get(d.keys().get(0)).orElseThrow();
                expectTypes(d, first, AlibabaPricingData.class, AlibabaInstance.class);
                data = d;
            } else if ("azure".equals(platform)) {
                AzurePricingData d;
                try {
                    d = BulkInstances.downloadAzurePricingData(
                            options(AzurePricingDataOptions.builder(), baseUrl, cachePath, token, cache).build());
                } catch (AWSPricingDataException e) {
                    throw providerException(e, AzurePricingDataException.class);
                }
                AzureInstance first = d.keys().isEmpty() ? null : d.get(d.keys().get(0)).orElseThrow();
                expectTypes(d, first, AzurePricingData.class, AzureInstance.class);
                data = d;
            } else if ("gcp".equals(platform)) {
                GCPPricingData d;
                try {
                    d = BulkInstances.downloadGcpPricingData(
                            options(GCPPricingDataOptions.builder(), baseUrl, cachePath, token, cache).build());
                } catch (AWSPricingDataException e) {
                    throw providerException(e, GCPPricingDataException.class);
                }
                GCPInstance first = d.keys().isEmpty() ? null : d.get(d.keys().get(0)).orElseThrow();
                expectTypes(d, first, GCPPricingData.class, GCPInstance.class);
                data = d;
            } else {
                AWSPricingDataOptions o = options(AWSPricingDataOptions.builder(), baseUrl, cachePath, token, cache).build();
                AWSPricingData d = platform == null
                        ? BulkInstances.downloadAwsEc2PricingData(o)
                        : BulkInstances.downloadAwsPricingData(platform, o);
                data = d;
            }
        } catch (AWSPricingDataException e) {
            error(g, e);
            return;
        }

        g.writeStartObject();
        g.writeStringField("offer", data.offer());
        g.writeArrayFieldStart("variantKeys");
        for (String k : data.variantKeys()) g.writeString(k);
        g.writeEndArray();
        g.writeArrayFieldStart("snapshots");
        for (Instant s : data.snapshots()) g.writeNumber(s.getEpochSecond());
        g.writeEndArray();
        g.writeObjectFieldStart("regions");
        for (var e : data.regions().entrySet()) {
            g.writeFieldName(e.getKey());
            map(g, e.getValue());
        }
        g.writeEndObject();
        List<String> keys = new ArrayList<>(data.keys());
        keys.sort(null);
        g.writeArrayFieldStart("keys");
        for (String k : keys) g.writeString(k);
        g.writeEndArray();
        g.writeObjectFieldStart("has");
        g.writeBooleanField("m5.large", data.has("m5.large"));
        g.writeBooleanField("nope", data.has("nope"));
        g.writeEndObject();
        g.writeFieldName("getMissing");
        if (data.get("nope").isPresent()) g.writeString("PRESENT"); else g.writeNull();

        List<String> locations = new ArrayList<>(data.regions().keySet());
        locations.add("Mystery");
        locations.add("Nowhere");
        g.writeObjectFieldStart("instances");
        for (String k : data.keys()) {
            g.writeFieldName(k);
            instance(g, data.get(k).orElseThrow(), locations);
        }
        g.writeEndObject();
        g.writeEndObject();
        g.flush();
        System.out.println();
    }

    static <B extends AWSPricingDataOptions.Builder> B options(
            B b, String baseUrl, String cachePath, String token, String cache) {
        b.baseUrl(baseUrl).cachePath(Path.of(cachePath)).cachePricingData(cache.equals("1"));
        if (!token.equals("-")) b.token(token);
        return b;
    }

    static <B extends AWSInstanceOptions.Builder> B instanceOptions(B b, String baseUrl, String token) {
        b.baseUrl(baseUrl);
        if (!token.equals("-")) b.token(token);
        return b;
    }

    /** {@code e}, if it is the provider's exception; exits 1 if it is another {@link AWSPricingDataException}. */
    static AWSPricingDataException providerException(
            AWSPricingDataException e, Class<? extends AWSPricingDataException> expected) {
        if (!expected.isInstance(e)) {
            System.err.println("expected a " + expected.getSimpleName() + ", got " + e.getClass().getSimpleName());
            System.exit(1);
        }
        return e;
    }

    /** Exits 1 unless the data and its first instance are exactly the provider's classes. */
    static void expectTypes(PricingData<?> d, AWSInstance first, Class<?> data, Class<?> instance) {
        if (d.getClass() != data || (first != null && first.getClass() != instance)) {
            System.err.println("expected " + data.getSimpleName() + " and " + instance.getSimpleName());
            System.exit(1);
        }
    }

    /** Exits 1 unless the instance, if there is one, is exactly the provider's class. */
    static void expectInstance(Optional<? extends AWSInstance> i, Class<?> instance) {
        if (i.isPresent() && i.get().getClass() != instance) {
            System.err.println("expected " + instance.getSimpleName());
            System.exit(1);
        }
    }

    static void error(JsonGenerator g, AWSPricingDataException e) throws IOException {
        g.writeStartObject();
        g.writeObjectFieldStart("error");
        g.writeFieldName("status");
        if (e.status().isPresent()) g.writeNumber(e.status().getAsInt()); else g.writeNull();
        g.writeStringField("message", e.getMessage());
        g.writeEndObject();
        g.writeEndObject();
        g.flush();
        System.out.println();
        System.exit(3);
    }

    static void instance(JsonGenerator g, AWSInstance i, List<String> locations) throws IOException {
        g.writeStartObject();
        g.writeStringField("name", i.name());
        g.writeNumberField("createdAt", i.createdAt().getEpochSecond());
        g.writeFieldName("deletedAt");
        ts(g, i.deletedAt());
        g.writeFieldName("attributes");
        map(g, i.attributes());
        g.writeObjectFieldStart("attributesIn");
        for (String r : locations) {
            g.writeFieldName(r);
            map(g, i.attributesIn(r));
        }
        g.writeEndObject();
        g.writeArrayFieldStart("attributesHistory");
        for (AttributeChange c : i.attributesHistory()) {
            g.writeStartObject();
            g.writeNumberField("at", c.at().getEpochSecond());
            g.writeStringField("key", c.key());
            g.writeStringField("value", c.value().orElse(null));
            g.writeStringField("region", c.region().orElse(null));
            g.writeEndObject();
        }
        g.writeEndArray();

        g.writeObjectFieldStart("pricing");
        g.writeArrayFieldStart("onDemand");
        for (OnDemandPrice p : i.pricing().onDemand()) {
            g.writeStartObject();
            head(g, p.location(), p.variant(), null);
            g.writeNumberField("hourly", p.hourly());
            g.writeNumberField("since", p.since().getEpochSecond());
            g.writeEndObject();
        }
        g.writeEndArray();
        g.writeArrayFieldStart("reserved");
        for (ReservedPrice p : i.pricing().reserved()) {
            g.writeStartObject();
            head(g, p.location(), p.variant(), p.term());
            g.writeNumberField("hourly", p.hourly());
            g.writeNumberField("upfront", p.upfront());
            g.writeNumberField("since", p.since().getEpochSecond());
            g.writeEndObject();
        }
        g.writeEndArray();
        g.writeEndObject();

        g.writeObjectFieldStart("pricingHistory");
        g.writeArrayFieldStart("onDemand");
        for (OnDemandPriceChange p : i.pricingHistory().onDemand()) {
            g.writeStartObject();
            head(g, p.location(), p.variant(), null);
            g.writeNumberField("at", p.at().getEpochSecond());
            num(g, "hourly", p.hourly());
            g.writeEndObject();
        }
        g.writeEndArray();
        g.writeArrayFieldStart("reserved");
        for (ReservedPriceChange p : i.pricingHistory().reserved()) {
            g.writeStartObject();
            head(g, p.location(), p.variant(), p.term());
            g.writeNumberField("at", p.at().getEpochSecond());
            num(g, "hourly", p.hourly());
            num(g, "upfront", p.upfront());
            g.writeEndObject();
        }
        g.writeEndArray();
        g.writeEndObject();
        g.writeEndObject();
    }

    static void map(JsonGenerator g, Map<String, String> m) throws IOException {
        g.writeStartObject();
        for (var e : m.entrySet()) g.writeStringField(e.getKey(), e.getValue());
        g.writeEndObject();
    }

    static void ts(JsonGenerator g, Optional<Instant> t) throws IOException {
        if (t.isPresent()) g.writeNumber(t.get().getEpochSecond()); else g.writeNull();
    }

    static void num(JsonGenerator g, String field, OptionalDouble d) throws IOException {
        g.writeFieldName(field);
        if (d.isPresent()) g.writeNumber(d.getAsDouble()); else g.writeNull();
    }

    static void head(JsonGenerator g, Location l, Variant v, ReservedTerm t) throws IOException {
        g.writeStringField("region", l.region());
        g.writeStringField("regionCode", l.regionCode().orElse(null));
        g.writeFieldName("variant");
        map(g, v.fields());
        g.writeStringField("operatingSystem", v.operatingSystem());
        g.writeStringField("tenancy", v.tenancy());
        g.writeStringField("licenseModel", v.licenseModel());
        g.writeStringField("preInstalledSw", v.preInstalledSw());
        g.writeStringField("capacitystatus", v.capacitystatus());
        if (t != null) {
            g.writeStringField("leaseContractLength", t.leaseContractLength());
            g.writeStringField("offeringClass", t.offeringClass());
            g.writeStringField("purchaseOption", t.purchaseOption());
        }
    }
}
