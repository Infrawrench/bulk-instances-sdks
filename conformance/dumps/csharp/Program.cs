using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using Infrawrench.BulkInstances;

var (baseUrl, cachePath, token, cache) = (args[0], args[1], args[2], args[3]);
var platform = args.Length > 4 ? args[4] : null;
static JsonNode? Ts(DateTimeOffset? d) => d is { } v ? v.ToUnixTimeSeconds() : null;
static JsonObject Dict(IReadOnlyDictionary<string, string> d) => new(d.Select(kv => KeyValuePair.Create(kv.Key, (JsonNode?)kv.Value)));
static JsonObject Loc(string region, string? regionCode) => new() { ["region"] = region, ["regionCode"] = regionCode };
static JsonObject Variant(JsonObject o, IReadOnlyDictionary<string, string> variant, string os, string tenancy, string license, string sw, string capacity)
{
    o["variant"] = Dict(variant);
    o["operatingSystem"] = os; o["tenancy"] = tenancy; o["licenseModel"] = license;
    o["preInstalledSw"] = sw; o["capacitystatus"] = capacity;
    return o;
}
static JsonObject Term(JsonObject o, string lease, string offering, string purchase)
{
    o["leaseContractLength"] = lease; o["offeringClass"] = offering; o["purchaseOption"] = purchase;
    return o;
}
static JsonArray Arr<T>(IEnumerable<T> xs, Func<T, JsonNode?> f) => new(xs.Select(f).ToArray());

AwsPricingData data;
try
{
    var options = new AwsPricingDataOptions
    {
        BaseUrl = baseUrl,
        CachePath = cachePath,
        CachePricingData = cache == "1",
        Token = token == "-" ? null : token,
    };
    data = platform is null
        ? await BulkInstances.DownloadAwsEc2PricingDataAsync(options)
        : await BulkInstances.DownloadAwsPricingDataAsync(platform, options);
}
catch (AwsPricingDataException e)
{
    Console.WriteLine(new JsonObject { ["error"] = new JsonObject { ["status"] = e.Status, ["message"] = e.Message } }.ToJsonString());
    return 3;
}

var regions = new JsonObject(data.Regions.Select(kv => KeyValuePair.Create(kv.Key, (JsonNode?)Dict(kv.Value))));
var instances = new JsonObject();
var output = new JsonObject
{
    ["offer"] = data.Offer,
    ["variantKeys"] = Arr(data.VariantKeys, k => k),
    ["snapshots"] = Arr(data.Snapshots, d => Ts(d)),
    ["regions"] = regions,
    ["keys"] = Arr(data.Keys.Order(StringComparer.Ordinal), k => k),
    ["has"] = new JsonObject { ["m5.large"] = data.Contains("m5.large"), ["nope"] = data.Contains("nope") },
    ["getMissing"] = data.Get("nope") is null ? null : "present",
    ["instances"] = instances,
};
foreach (var k in data.Keys)
{
    var i = data.Get(k)!;
    var p = i.Pricing;
    var h = i.PricingHistory;
    var attributesIn = new JsonObject();
    foreach (var r in data.Regions.Keys.Append("Mystery").Append("Nowhere")) attributesIn[r] = Dict(i.AttributesIn(r));
    instances[k] = new JsonObject
    {
        ["name"] = i.Name,
        ["createdAt"] = Ts(i.CreatedAt),
        ["deletedAt"] = Ts(i.DeletedAt),
        ["attributes"] = Dict(i.Attributes),
        ["attributesIn"] = attributesIn,
        ["attributesHistory"] = Arr(i.AttributesHistory, c => new JsonObject
        {
            ["at"] = Ts(c.At), ["key"] = c.Key, ["value"] = c.Value, ["region"] = c.Region,
        }),
        ["pricing"] = new JsonObject
        {
            ["onDemand"] = Arr(p.OnDemand, r =>
            {
                var o = Variant(Loc(r.Region, r.RegionCode), r.Variant, r.OperatingSystem, r.Tenancy, r.LicenseModel, r.PreInstalledSw, r.Capacitystatus);
                o["hourly"] = r.Hourly; o["since"] = Ts(r.Since);
                return o;
            }),
            ["reserved"] = Arr(p.Reserved, r =>
            {
                var o = Term(Variant(Loc(r.Region, r.RegionCode), r.Variant, r.OperatingSystem, r.Tenancy, r.LicenseModel, r.PreInstalledSw, r.Capacitystatus),
                    r.LeaseContractLength, r.OfferingClass, r.PurchaseOption);
                o["hourly"] = r.Hourly; o["upfront"] = r.Upfront; o["since"] = Ts(r.Since);
                return o;
            }),
        },
        ["pricingHistory"] = new JsonObject
        {
            ["onDemand"] = Arr(h.OnDemand, r =>
            {
                var o = Variant(Loc(r.Region, r.RegionCode), r.Variant, r.OperatingSystem, r.Tenancy, r.LicenseModel, r.PreInstalledSw, r.Capacitystatus);
                o["at"] = Ts(r.At); o["hourly"] = r.Hourly;
                return o;
            }),
            ["reserved"] = Arr(h.Reserved, r =>
            {
                var o = Term(Variant(Loc(r.Region, r.RegionCode), r.Variant, r.OperatingSystem, r.Tenancy, r.LicenseModel, r.PreInstalledSw, r.Capacitystatus),
                    r.LeaseContractLength, r.OfferingClass, r.PurchaseOption);
                o["at"] = Ts(r.At); o["hourly"] = r.Hourly; o["upfront"] = r.Upfront;
                return o;
            }),
        },
    };
}
Console.WriteLine(output.ToJsonString(new JsonSerializerOptions { WriteIndented = true, Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping }));
return 0;
