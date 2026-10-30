package com.infrawrench.bulkinstances;

import static com.fasterxml.jackson.core.JsonToken.END_ARRAY;
import static com.fasterxml.jackson.core.JsonToken.START_ARRAY;
import static com.fasterxml.jackson.core.JsonToken.START_OBJECT;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Streams the bundle JSON into compact raw rows. The bundle is about 210 MB of small arrays, which a JSON tree
 * would hold as tens of millions of nodes; here each section of an instance is one primitive array.
 */
final class BundleParser {
    private static final JsonFactory FACTORY = new JsonFactory();

    private BundleParser() {}

    /** One {@code regions} entry: {@code [location, [[key, value], ...]]}. */
    record RawRegion(double location, Rows pairs) {}

    static AWSPricingData parse(InputStream in) throws IOException {
        return parse(in, false);
    }

    /**
     * One instance as the Infrawrench API serves it: the bundle's tables cut down to what it uses, with {@code name}
     * and {@code instance} in place of {@code instances}. The result holds just that instance.
     */
    static AWSPricingData parseInstance(InputStream in) throws IOException {
        return parse(in, true);
    }

    private static AWSPricingData parse(InputStream in, boolean oneInstance) throws IOException {
        try (JsonParser p = FACTORY.createParser(in)) {
            p.nextToken();
            Rows.expect(p, START_OBJECT);
            String offer = null;
            String[] table = new String[0];
            double[] snapshots = new double[0];
            List<RawRegion> regions = List.of();
            List<String> variantKeys = null;
            List<double[]> variants = List.of();
            Rows terms = Rows.EMPTY;
            Map<String, RawInstance> instances = new LinkedHashMap<>();
            String name = null;
            RawInstance instance = null;
            for (String field; (field = p.nextFieldName()) != null; ) {
                p.nextToken();
                switch (field) {
                    case "offer" -> offer = p.currentToken() == JsonToken.VALUE_NULL ? null : string(p);
                    case "compression_table" -> table = strings(p);
                    case "snapshots" -> snapshots = numbers(p);
                    case "regions" -> regions = regions(p);
                    case "variant_keys" -> variantKeys = p.currentToken() == JsonToken.VALUE_NULL ? null : keys(p);
                    case "variants" -> variants = variants(p);
                    case "reserved_terms" -> terms = Rows.parse(p, 3);
                    case "instances" -> instances = instances(p);
                    case "name" -> {
                        if (oneInstance) name = string(p);
                        else p.skipChildren();
                    }
                    case "instance" -> {
                        if (oneInstance) instance = instance(p);
                        else p.skipChildren();
                    }
                    default -> p.skipChildren();
                }
            }
            if (p.nextToken() != null) throw new JsonParseException(p, "Unexpected content after the bundle");
            if (oneInstance) {
                if (name == null || instance == null) throw new IOException("The instance has no name or rows");
                instances = Map.of(name, instance);
            }
            if (offer == null) offer = "AmazonEC2";
            if (variantKeys == null) variantKeys = BulkInstances.EC2_VARIANT_KEYS;
            for (double[] v : variants) {
                if (v.length != variantKeys.size()) {
                    throw new IOException("variant has " + v.length + " fields, expected " + variantKeys.size());
                }
            }
            return new AWSPricingData(offer, table, snapshots, regions, variantKeys, variants, terms, instances);
        }
    }

    private static String string(JsonParser p) throws IOException {
        if (p.currentToken() != JsonToken.VALUE_STRING) {
            throw new JsonParseException(p, "Expected a string, got " + p.currentToken());
        }
        return p.getText();
    }

    /** {@code variant_keys}: strings, unlike {@code compression_table}, never {@code null}. */
    private static List<String> keys(JsonParser p) throws IOException {
        Rows.expect(p, START_ARRAY);
        List<String> out = new ArrayList<>();
        while (p.nextToken() != END_ARRAY) out.add(string(p));
        return List.copyOf(out);
    }

    /** {@code variants}: rows as long as {@code variant_keys}, which may come after them. */
    private static List<double[]> variants(JsonParser p) throws IOException {
        Rows.expect(p, START_ARRAY);
        List<double[]> out = new ArrayList<>();
        while (p.nextToken() != END_ARRAY) out.add(numbers(p));
        return out;
    }

    private static String[] strings(JsonParser p) throws IOException {
        Rows.expect(p, START_ARRAY);
        List<String> out = new ArrayList<>();
        for (JsonToken t; (t = p.nextToken()) != END_ARRAY; ) {
            if (t != JsonToken.VALUE_STRING && t != JsonToken.VALUE_NULL) {
                throw new JsonParseException(p, "Expected a string, got " + t);
            }
            out.add(p.getValueAsString());
        }
        return out.toArray(String[]::new);
    }

    private static double[] numbers(JsonParser p) throws IOException {
        Rows.expect(p, START_ARRAY);
        double[] out = new double[16];
        int n = 0;
        for (JsonToken t; (t = p.nextToken()) != END_ARRAY; ) {
            if (n == out.length) out = Arrays.copyOf(out, n * 2);
            out[n++] = Rows.number(p, t);
        }
        return Arrays.copyOf(out, n);
    }

    private static List<RawRegion> regions(JsonParser p) throws IOException {
        Rows.expect(p, START_ARRAY);
        List<RawRegion> out = new ArrayList<>();
        while (p.nextToken() != END_ARRAY) {
            Rows.expect(p, START_ARRAY);
            double location = Rows.number(p, p.nextToken());
            p.nextToken();
            Rows pairs = Rows.parse(p, 2);
            while (p.nextToken() != END_ARRAY) p.skipChildren();
            out.add(new RawRegion(location, pairs));
        }
        return out;
    }

    private static Map<String, RawInstance> instances(JsonParser p) throws IOException {
        Rows.expect(p, START_OBJECT);
        Map<String, RawInstance> out = new LinkedHashMap<>();
        for (String name; (name = p.nextFieldName()) != null; ) {
            p.nextToken();
            out.put(name, instance(p));
        }
        return out;
    }

    private static RawInstance instance(JsonParser p) throws IOException {
        Rows.expect(p, START_ARRAY);
        Rows attrs = Rows.EMPTY, attrChanges = Rows.EMPTY, onDemand = Rows.EMPTY, reserved = Rows.EMPTY;
        double basePrice = Double.NaN, createdAt = Double.NaN, deletedAt = Double.NaN;
        int i = 0;
        for (JsonToken t; (t = p.nextToken()) != END_ARRAY; i++) {
            switch (i) {
                case 0 -> attrs = Rows.parse(p, 2);
                case 1 -> attrChanges = Rows.parse(p, 4);
                case 2 -> basePrice = Rows.number(p, t);
                case 3 -> onDemand = Rows.parse(p, 4);
                case 4 -> reserved = Rows.parse(p, 6);
                case 5 -> createdAt = Rows.number(p, t);
                case 6 -> deletedAt = Rows.number(p, t);
                default -> p.skipChildren();
            }
        }
        return new RawInstance(attrs, attrChanges, basePrice, onDemand, reserved, createdAt, deletedAt);
    }
}
