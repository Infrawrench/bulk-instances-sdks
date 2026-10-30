using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// One AWS platform's pricing data, keyed by instance type.
/// </summary>
/// <remarks>
/// <para>
/// Nothing is decoded until it is asked for: <see cref="Get"/> wraps the raw rows, and each
/// property of the returned <see cref="AwsInstance"/> decodes its part on first access
/// and keeps the result.
/// </para>
/// <para>
/// The bundle is held as its UTF-8 JSON. Loading reads it once, keeping the string table and
/// where each instance's rows are; an instance's rows are only parsed when it is first asked for.
/// Lazy decoding is not locked: it is safe to read from several threads, but a part first accessed
/// concurrently may be decoded more than once.
/// </para>
/// </remarks>
public sealed class AwsPricingData
{
    private readonly byte[] _utf8;
    private readonly string[] _table;
    private readonly JsonElement _snapshotsRaw;
    private readonly JsonElement _regionsRaw;
    private readonly JsonElement _variantsRaw;
    private readonly JsonElement _termsRaw;
    private readonly Dictionary<string, (int Start, int Length)> _rawInstances;
    private readonly ConcurrentDictionary<string, AwsInstance> _instances = new(StringComparer.Ordinal);
    private IReadOnlyList<DateTimeOffset>? _snapshots;
    private IReadOnlyDictionary<string, IReadOnlyDictionary<string, string>>? _regions;
    private VariantFields[]? _variants;
    private ReservedTerm[]? _terms;

    /// <summary>Parses a bundle as instances-bundler writes it; every string is an index into <c>compression_table</c>.</summary>
    internal AwsPricingData(byte[] utf8Json)
    {
        _utf8 = utf8Json;
        string[]? table = null, variantKeys = null;
        string? offer = null;
        JsonElement? snapshots = null, regions = null, variants = null, terms = null;
        Dictionary<string, (int, int)>? instances = null;
        var keys = new List<string>();

        var reader = new Utf8JsonReader(utf8Json);
        Expect(ref reader, JsonTokenType.StartObject);
        while (reader.Read() && reader.TokenType == JsonTokenType.PropertyName)
        {
            var property = reader.GetString();
            reader.Read();
            switch (property)
            {
                case "compression_table":
                    table = ReadStrings(ref reader, property);
                    break;
                case "offer":
                    offer = reader.TokenType == JsonTokenType.Null ? null : reader.GetString();
                    break;
                case "variant_keys":
                    variantKeys = reader.TokenType == JsonTokenType.Null ? null : ReadStrings(ref reader, property);
                    break;
                case "snapshots":
                    snapshots = JsonElement.ParseValue(ref reader);
                    break;
                case "regions":
                    regions = JsonElement.ParseValue(ref reader);
                    break;
                case "variants":
                    variants = JsonElement.ParseValue(ref reader);
                    break;
                case "reserved_terms":
                    terms = JsonElement.ParseValue(ref reader);
                    break;
                case "instances":
                    instances = ReadRanges(ref reader, keys);
                    break;
                default:
                    reader.Skip();
                    break;
            }
        }
        // Validates that nothing follows the bundle.
        reader.Read();

        _table = table ?? throw Missing("compression_table");
        _snapshotsRaw = snapshots ?? throw Missing("snapshots");
        _regionsRaw = regions ?? throw Missing("regions");
        _variantsRaw = variants ?? throw Missing("variants");
        _termsRaw = terms ?? throw Missing("reserved_terms");
        _rawInstances = instances ?? throw Missing("instances");
        Keys = keys.AsReadOnly();
        // EC2 bundles leave out both.
        Offer = offer ?? "AmazonEC2";
        VariantKeys = variantKeys is null ? BulkInstances.Ec2VariantKeys : Array.AsReadOnly(variantKeys);
    }

    /// <summary>The AWS offer code, e.g. <c>AmazonEC2</c> or <c>AmazonRDS</c>.</summary>
    public string Offer { get; }

    /// <summary>
    /// The names of the fields that pick a price, which every price's <c>Variant</c> is keyed by.
    /// EC2 bundles don't list them, so they are <see cref="BulkInstances.Ec2VariantKeys"/>.
    /// </summary>
    public IReadOnlyList<string> VariantKeys { get; }

    /// <summary>Every instance type in the bundle, including ones AWS no longer lists (see <see cref="AwsInstance.DeletedAt"/>).</summary>
    public IReadOnlyList<string> Keys { get; }

    /// <summary>Whether the bundle has ever listed this instance type.</summary>
    /// <param name="instanceType">e.g. <c>m5.large</c>.</param>
    public bool Contains(string instanceType) => _rawInstances.ContainsKey(instanceType);

    /// <summary>The instance with this type (e.g. <c>m5.large</c>), or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="instanceType">e.g. <c>m5.large</c>.</param>
    public AwsInstance? Get(string instanceType)
    {
        TryGet(instanceType, out var instance);
        return instance;
    }

    /// <summary>Gets the instance with this type (e.g. <c>m5.large</c>), if the bundle has ever listed it.</summary>
    /// <param name="instanceType">e.g. <c>m5.large</c>.</param>
    /// <param name="instance">The instance, or <c>null</c> when this returns false.</param>
    public bool TryGet(string instanceType, [NotNullWhen(true)] out AwsInstance? instance)
    {
        if (_instances.TryGetValue(instanceType, out instance)) return true;
        if (!_rawInstances.TryGetValue(instanceType, out var range))
        {
            instance = null;
            return false;
        }
        var raw = JsonDocument.Parse(_utf8.AsMemory(range.Start, range.Length)).RootElement;
        instance = _instances.GetOrAdd(instanceType, new AwsInstance(instanceType, raw, this));
        return true;
    }

    /// <summary>The publication date of every AWS price list in the bundle, oldest first.</summary>
    public IReadOnlyList<DateTimeOffset> Snapshots =>
        _snapshots ??= _snapshotsRaw.EnumerateArray().Select(Date).ToList().AsReadOnly();

    /// <summary>Attributes of each AWS location (<c>regionCode</c>, <c>locationType</c>), keyed by location name.</summary>
    public IReadOnlyDictionary<string, IReadOnlyDictionary<string, string>> Regions =>
        _regions ??= DecodeRegions();

    private ReadOnlyDictionary<string, IReadOnlyDictionary<string, string>> DecodeRegions()
    {
        var regions = new Dictionary<string, IReadOnlyDictionary<string, string>>(StringComparer.Ordinal);
        foreach (var row in _regionsRaw.EnumerateArray())
        {
            var attrs = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var pair in row[1].EnumerateArray())
            {
                attrs[Str(pair[0])] = Str(pair[1]);
            }
            regions[Str(row[0])] = attrs.AsReadOnly();
        }
        return regions.AsReadOnly();
    }

    internal static DateTimeOffset Date(JsonElement ts) =>
        DateTimeOffset.FromUnixTimeMilliseconds((long)(ts.GetDouble() * 1000));

    internal string Str(JsonElement i) => Str(i.GetInt32());

    internal string Str(int i)
    {
        if ((uint)i >= (uint)_table.Length) throw new InvalidDataException($"string index {i} out of range");
        return _table[i];
    }

    internal (string Region, string? RegionCode) Location(JsonElement i)
    {
        var region = Str(i);
        string? regionCode = null;
        if (Regions.TryGetValue(region, out var attrs)) attrs.TryGetValue("regionCode", out regionCode);
        return (region, regionCode);
    }

    internal VariantFields Variant(JsonElement i)
    {
        _variants ??= DecodeVariants();
        return _variants[i.GetInt32()];
    }

    private VariantFields[] DecodeVariants()
    {
        var keys = VariantKeys;
        var layout = new VariantLayout(keys);
        return _variantsRaw.EnumerateArray()
            .Select(fields =>
            {
                var length = fields.GetArrayLength();
                if (length != keys.Count) throw new InvalidDataException($"variant has {length} fields, expected {keys.Count}");
                // A repeated key keeps its first position and its last value.
                var values = new string[layout.Keys.Length];
                for (var j = 0; j < length; j++) values[layout.Index[keys[j]]] = Str(fields[j]);
                var variant = new VariantMap(layout, values);
                return new VariantFields(
                    variant,
                    variant.GetOrEmpty("operatingSystem"),
                    variant.GetOrEmpty("tenancy"),
                    variant.GetOrEmpty("licenseModel"),
                    variant.GetOrEmpty("preInstalledSw"),
                    variant.GetOrEmpty("capacitystatus"));
            })
            .ToArray();
    }

    internal ReservedTerm Term(JsonElement i)
    {
        _terms ??= _termsRaw.EnumerateArray()
            .Select(t => new ReservedTerm(Str(t[0]), Str(t[1]), Str(t[2])))
            .ToArray();
        return _terms[i.GetInt32()];
    }

    private static void Expect(ref Utf8JsonReader reader, JsonTokenType type)
    {
        if (!reader.Read() || reader.TokenType != type) throw new JsonException($"Expected {type} in the bundle.");
    }

    private static JsonException Missing(string property) => new($"The bundle has no {property}.");

    private static string[] ReadStrings(ref Utf8JsonReader reader, string property)
    {
        if (reader.TokenType != JsonTokenType.StartArray) throw new JsonException($"{property} is not an array.");
        var strings = new List<string>();
        while (reader.Read() && reader.TokenType != JsonTokenType.EndArray)
        {
            strings.Add(reader.GetString() ?? throw new JsonException($"{property} holds a null."));
        }
        return strings.ToArray();
    }

    /// <summary>Where each instance's raw rows are in the UTF-8 JSON, without parsing them into a document.</summary>
    private static Dictionary<string, (int, int)> ReadRanges(ref Utf8JsonReader reader, List<string> keys)
    {
        if (reader.TokenType != JsonTokenType.StartObject) throw new JsonException("instances is not an object.");
        var ranges = new Dictionary<string, (int, int)>(StringComparer.Ordinal);
        while (reader.Read() && reader.TokenType == JsonTokenType.PropertyName)
        {
            var name = reader.GetString()!;
            reader.Read();
            var start = (int)reader.TokenStartIndex;
            reader.Skip();
            if (!ranges.ContainsKey(name)) keys.Add(name);
            ranges[name] = (start, (int)reader.BytesConsumed - start);
        }
        return ranges;
    }
}
