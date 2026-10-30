using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>One instance type. Each property decodes on first access and caches the result.</summary>
public sealed class AwsInstance
{
    // [attrs, attrChanges, basePrice, onDemand, reserved, createdAt, deletedAt]
    private readonly JsonElement _raw;
    private readonly AwsPricingData _data;
    private IReadOnlyDictionary<string, string>? _attributes;
    private IReadOnlyList<AttributeChange>? _attributesHistory;
    private Pricing? _pricing;
    private PricingHistory? _pricingHistory;

    internal AwsInstance(string name, JsonElement raw, AwsPricingData data)
    {
        Name = name;
        _raw = raw;
        _data = data;
    }

    /// <summary>The instance type, e.g. <c>m5.large</c>.</summary>
    public string Name { get; }

    /// <summary>The publication date of the first price list that listed this instance.</summary>
    public DateTimeOffset CreatedAt => AwsPricingData.Date(_raw[5]);

    /// <summary>The publication date of the first price list that stopped listing it, or <c>null</c> if AWS still lists it.</summary>
    public DateTimeOffset? DeletedAt => Optional(_raw, 6) is { } ts ? AwsPricingData.Date(ts) : null;

    /// <summary>The latest attributes shared by every region. Regional differences are in <see cref="AttributesIn"/>.</summary>
    public IReadOnlyDictionary<string, string> Attributes
    {
        get
        {
            if (_attributes is null)
            {
                var attributes = new Dictionary<string, string>(StringComparer.Ordinal);
                foreach (var c in AttributesHistory)
                {
                    if (c.Region is not null) continue;
                    if (c.Value is null) attributes.Remove(c.Key);
                    else attributes[c.Key] = c.Value;
                }
                _attributes = attributes.AsReadOnly();
            }
            return _attributes;
        }
    }

    /// <summary>
    /// The latest attributes in one AWS location (e.g. <c>US East (N. Virginia)</c>): the
    /// global ones with that region's overrides on top. A regional override keeps
    /// applying even after a newer global change to the same key.
    /// </summary>
    /// <param name="region">The AWS location name.</param>
    /// <returns>A new dictionary on every call.</returns>
    public IReadOnlyDictionary<string, string> AttributesIn(string region)
    {
        var attributes = new Dictionary<string, string>(Attributes, StringComparer.Ordinal);
        foreach (var c in AttributesHistory)
        {
            if (c.Region != region) continue;
            if (c.Value is null) attributes.Remove(c.Key);
            else attributes[c.Key] = c.Value;
        }
        return attributes;
    }

    /// <summary>Every attribute change, oldest first, starting with the attributes the instance was first listed with.</summary>
    public IReadOnlyList<AttributeChange> AttributesHistory
    {
        get
        {
            if (_attributesHistory is null)
            {
                var d = _data;
                var created = CreatedAt;
                var initial = _raw[0].EnumerateArray()
                    .Select(kv => new AttributeChange(created, d.Str(kv[0]), d.Str(kv[1]), null));
                // [ts, key, value: omitted or null = removed, region: omitted or null = every region]
                var changes = _raw[1].EnumerateArray()
                    .Select(row => new AttributeChange(
                        AwsPricingData.Date(row[0]),
                        d.Str(row[1]),
                        Optional(row, 2) is { } value ? d.Str(value) : null,
                        Optional(row, 3) is { } region ? d.Str(region) : null))
                    // OrderBy is stable, so rows with the same timestamp keep their order (later rows win).
                    .OrderBy(c => c.At);
                _attributesHistory = initial.Concat(changes).ToList().AsReadOnly();
            }
            return _attributesHistory;
        }
    }

    /// <summary>The current price of everything still offered.</summary>
    public Pricing Pricing
    {
        get
        {
            if (_pricing is null)
            {
                var history = PricingHistory;
                var onDemand = Latest(history.OnDemand, OnDemandKey)
                    .Where(r => r.Hourly is not null)
                    .Select(r => new OnDemandPrice
                    {
                        Region = r.Region,
                        RegionCode = r.RegionCode,
                        Variant = r.Variant,
                        OperatingSystem = r.OperatingSystem,
                        Tenancy = r.Tenancy,
                        LicenseModel = r.LicenseModel,
                        PreInstalledSw = r.PreInstalledSw,
                        Capacitystatus = r.Capacitystatus,
                        Hourly = r.Hourly!.Value,
                        Since = r.At,
                    });
                var reserved = Latest(history.Reserved, r => string.Join('\0', OnDemandKey(r), r.LeaseContractLength, r.OfferingClass, r.PurchaseOption))
                    .Where(r => r.Hourly is not null)
                    .Select(r => new ReservedPrice
                    {
                        Region = r.Region,
                        RegionCode = r.RegionCode,
                        Variant = r.Variant,
                        OperatingSystem = r.OperatingSystem,
                        Tenancy = r.Tenancy,
                        LicenseModel = r.LicenseModel,
                        PreInstalledSw = r.PreInstalledSw,
                        Capacitystatus = r.Capacitystatus,
                        LeaseContractLength = r.LeaseContractLength,
                        OfferingClass = r.OfferingClass,
                        PurchaseOption = r.PurchaseOption,
                        Hourly = r.Hourly!.Value,
                        Upfront = r.Upfront ?? 0,
                        Since = r.At,
                    });
                _pricing = new Pricing(onDemand.ToList().AsReadOnly(), reserved.ToList().AsReadOnly());
            }
            return _pricing;
        }
    }

    /// <summary>Every on-demand and reserved price change, oldest first.</summary>
    public PricingHistory PricingHistory
    {
        get
        {
            if (_pricingHistory is null)
            {
                var d = _data;
                var basePrice = _raw[2].GetDouble();
                // [ts, region, variant, price: omitted = base price, null = no longer offered]
                var onDemand = _raw[3].EnumerateArray()
                    .Select(row =>
                    {
                        var (region, regionCode) = d.Location(row[1]);
                        var v = d.Variant(row[2]);
                        return new OnDemandPriceChange
                        {
                            At = AwsPricingData.Date(row[0]),
                            Region = region,
                            RegionCode = regionCode,
                            Variant = v.Fields,
                            OperatingSystem = v.OperatingSystem,
                            Tenancy = v.Tenancy,
                            LicenseModel = v.LicenseModel,
                            PreInstalledSw = v.PreInstalledSw,
                            Capacitystatus = v.Capacitystatus,
                            Hourly = row.GetArrayLength() <= 3 ? basePrice : Optional(row, 3)?.GetDouble(),
                        };
                    })
                    .OrderBy(r => r.At);
                // [ts, region, variant, term, hourly: null = no longer offered, upfront: omitted if 0]
                var reserved = _raw[4].EnumerateArray()
                    .Select(row =>
                    {
                        var (region, regionCode) = d.Location(row[1]);
                        var v = d.Variant(row[2]);
                        var t = d.Term(row[3]);
                        var hourly = Optional(row, 4)?.GetDouble();
                        return new ReservedPriceChange
                        {
                            At = AwsPricingData.Date(row[0]),
                            Region = region,
                            RegionCode = regionCode,
                            Variant = v.Fields,
                            OperatingSystem = v.OperatingSystem,
                            Tenancy = v.Tenancy,
                            LicenseModel = v.LicenseModel,
                            PreInstalledSw = v.PreInstalledSw,
                            Capacitystatus = v.Capacitystatus,
                            LeaseContractLength = t.LeaseContractLength,
                            OfferingClass = t.OfferingClass,
                            PurchaseOption = t.PurchaseOption,
                            Hourly = hourly,
                            Upfront = hourly is null ? null : Optional(row, 5)?.GetDouble() ?? 0,
                        };
                    })
                    .OrderBy(r => r.At);
                _pricingHistory = new PricingHistory(onDemand.ToList().AsReadOnly(), reserved.ToList().AsReadOnly());
            }
            return _pricingHistory;
        }
    }

    /// <summary>The last row for each key, with keys in order of first appearance.</summary>
    private static IEnumerable<T> Latest<T>(IEnumerable<T> rows, Func<T, string> key)
    {
        var index = new Dictionary<string, int>(StringComparer.Ordinal);
        var latest = new List<T>();
        foreach (var r in rows)
        {
            var k = key(r);
            if (index.TryGetValue(k, out var i)) latest[i] = r;
            else
            {
                index[k] = latest.Count;
                latest.Add(r);
            }
        }
        return latest;
    }

    // The whole variant, not just EC2's fields: RDS's Single-AZ and Multi-AZ prices differ only in deploymentOption.
    private static string OnDemandKey(OnDemandPriceChange r) => VariantKey(r.Region, r.Variant);

    private static string OnDemandKey(ReservedPriceChange r) => VariantKey(r.Region, r.Variant);

    private static string VariantKey(string region, IReadOnlyDictionary<string, string> variant) =>
        string.Join('\0', variant.Values.Prepend(region));

    /// <summary>Element <paramref name="i"/> of a row, or <c>null</c> if the row is shorter or holds <c>null</c> there.</summary>
    private static JsonElement? Optional(JsonElement row, int i) =>
        i < row.GetArrayLength() && row[i].ValueKind != JsonValueKind.Null ? row[i] : null;
}
