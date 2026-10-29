import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonGenerator;
import com.infrawrench.bulkinstances.AWSInstance;
import com.infrawrench.bulkinstances.AWSPricingData;
import com.infrawrench.bulkinstances.AWSPricingDataException;
import com.infrawrench.bulkinstances.AWSPricingDataOptions;
import com.infrawrench.bulkinstances.AttributeChange;
import com.infrawrench.bulkinstances.BulkInstances;
import com.infrawrench.bulkinstances.Location;
import com.infrawrench.bulkinstances.OnDemandPrice;
import com.infrawrench.bulkinstances.OnDemandPriceChange;
import com.infrawrench.bulkinstances.ReservedPrice;
import com.infrawrench.bulkinstances.ReservedPriceChange;
import com.infrawrench.bulkinstances.ReservedTerm;
import com.infrawrench.bulkinstances.Variant;
import java.io.IOException;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalDouble;

public final class Dump {
    public static void main(String[] args) throws IOException {
        String baseUrl = args[0], cachePath = args[1], token = args[2], cache = args[3];
        JsonGenerator g = new JsonFactory().createGenerator(System.out);
        AWSPricingData data;
        try {
            AWSPricingDataOptions.Builder b = AWSPricingDataOptions.builder()
                    .baseUrl(baseUrl).cachePath(Path.of(cachePath)).cachePricingData(cache.equals("1"));
            if (!token.equals("-")) b.token(token);
            data = BulkInstances.downloadAwsEc2PricingData(b.build());
        } catch (AWSPricingDataException e) {
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
            return;
        }

        g.writeStartObject();
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
            AWSInstance i = data.get(k).orElseThrow();
            g.writeObjectFieldStart(k);
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
        g.writeEndObject();
        g.writeEndObject();
        g.flush();
        System.out.println();
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
