using System;
using System.Collections.Generic;

namespace Infrawrench.BulkInstances;

/// <summary>The current on-demand price of one product (location and the product fields that pick a price).</summary>
public sealed record OnDemandPrice
{
    /// <summary>The AWS location name, e.g. <c>US East (N. Virginia)</c>.</summary>
    public required string Region { get; init; }

    /// <summary>e.g. <c>us-east-1</c>. <c>null</c> for locations the price list never gave a code.</summary>
    public string? RegionCode { get; init; }

    /// <summary>e.g. <c>Linux</c>.</summary>
    public required string OperatingSystem { get; init; }

    /// <summary>e.g. <c>Shared</c>.</summary>
    public required string Tenancy { get; init; }

    /// <summary>e.g. <c>No License required</c>.</summary>
    public required string LicenseModel { get; init; }

    /// <summary>e.g. <c>NA</c>.</summary>
    public required string PreInstalledSw { get; init; }

    /// <summary>e.g. <c>Used</c>.</summary>
    public required string Capacitystatus { get; init; }

    /// <summary>USD per hour.</summary>
    public required double Hourly { get; init; }

    /// <summary>When this price took effect.</summary>
    public required DateTimeOffset Since { get; init; }
}

/// <summary>The current price of one reserved product.</summary>
public sealed record ReservedPrice
{
    /// <summary>The AWS location name, e.g. <c>US East (N. Virginia)</c>.</summary>
    public required string Region { get; init; }

    /// <summary>e.g. <c>us-east-1</c>. <c>null</c> for locations the price list never gave a code.</summary>
    public string? RegionCode { get; init; }

    /// <summary>e.g. <c>Linux</c>.</summary>
    public required string OperatingSystem { get; init; }

    /// <summary>e.g. <c>Shared</c>.</summary>
    public required string Tenancy { get; init; }

    /// <summary>e.g. <c>No License required</c>.</summary>
    public required string LicenseModel { get; init; }

    /// <summary>e.g. <c>NA</c>.</summary>
    public required string PreInstalledSw { get; init; }

    /// <summary>e.g. <c>Used</c>.</summary>
    public required string Capacitystatus { get; init; }

    /// <summary>e.g. <c>1yr</c>.</summary>
    public required string LeaseContractLength { get; init; }

    /// <summary>e.g. <c>standard</c>.</summary>
    public required string OfferingClass { get; init; }

    /// <summary>e.g. <c>No Upfront</c>.</summary>
    public required string PurchaseOption { get; init; }

    /// <summary>USD per hour.</summary>
    public required double Hourly { get; init; }

    /// <summary>USD paid up front.</summary>
    public required double Upfront { get; init; }

    /// <summary>When this price took effect.</summary>
    public required DateTimeOffset Since { get; init; }
}

/// <summary>The current price of everything still offered.</summary>
/// <param name="OnDemand">On-demand prices.</param>
/// <param name="Reserved">Reserved prices.</param>
public sealed record Pricing(IReadOnlyList<OnDemandPrice> OnDemand, IReadOnlyList<ReservedPrice> Reserved);

/// <summary>One change of an on-demand price.</summary>
public sealed record OnDemandPriceChange
{
    /// <summary>When the change took effect.</summary>
    public required DateTimeOffset At { get; init; }

    /// <summary>The AWS location name, e.g. <c>US East (N. Virginia)</c>.</summary>
    public required string Region { get; init; }

    /// <summary>e.g. <c>us-east-1</c>. <c>null</c> for locations the price list never gave a code.</summary>
    public string? RegionCode { get; init; }

    /// <summary>e.g. <c>Linux</c>.</summary>
    public required string OperatingSystem { get; init; }

    /// <summary>e.g. <c>Shared</c>.</summary>
    public required string Tenancy { get; init; }

    /// <summary>e.g. <c>No License required</c>.</summary>
    public required string LicenseModel { get; init; }

    /// <summary>e.g. <c>NA</c>.</summary>
    public required string PreInstalledSw { get; init; }

    /// <summary>e.g. <c>Used</c>.</summary>
    public required string Capacitystatus { get; init; }

    /// <summary><c>null</c> means no longer offered from <see cref="At"/> on.</summary>
    public required double? Hourly { get; init; }
}

/// <summary>One change of a reserved price.</summary>
public sealed record ReservedPriceChange
{
    /// <summary>When the change took effect.</summary>
    public required DateTimeOffset At { get; init; }

    /// <summary>The AWS location name, e.g. <c>US East (N. Virginia)</c>.</summary>
    public required string Region { get; init; }

    /// <summary>e.g. <c>us-east-1</c>. <c>null</c> for locations the price list never gave a code.</summary>
    public string? RegionCode { get; init; }

    /// <summary>e.g. <c>Linux</c>.</summary>
    public required string OperatingSystem { get; init; }

    /// <summary>e.g. <c>Shared</c>.</summary>
    public required string Tenancy { get; init; }

    /// <summary>e.g. <c>No License required</c>.</summary>
    public required string LicenseModel { get; init; }

    /// <summary>e.g. <c>NA</c>.</summary>
    public required string PreInstalledSw { get; init; }

    /// <summary>e.g. <c>Used</c>.</summary>
    public required string Capacitystatus { get; init; }

    /// <summary>e.g. <c>1yr</c>.</summary>
    public required string LeaseContractLength { get; init; }

    /// <summary>e.g. <c>standard</c>.</summary>
    public required string OfferingClass { get; init; }

    /// <summary>e.g. <c>No Upfront</c>.</summary>
    public required string PurchaseOption { get; init; }

    /// <summary><c>null</c> means no longer offered from <see cref="At"/> on.</summary>
    public required double? Hourly { get; init; }

    /// <summary>USD paid up front; <c>null</c> when <see cref="Hourly"/> is.</summary>
    public required double? Upfront { get; init; }
}

/// <summary>Every on-demand and reserved price change.</summary>
/// <param name="OnDemand">Oldest first.</param>
/// <param name="Reserved">Oldest first.</param>
public sealed record PricingHistory(IReadOnlyList<OnDemandPriceChange> OnDemand, IReadOnlyList<ReservedPriceChange> Reserved);

/// <summary>One attribute change.</summary>
/// <param name="At">When the change took effect.</param>
/// <param name="Key">The attribute name, e.g. <c>vcpu</c>.</param>
/// <param name="Value"><c>null</c> means the attribute was removed.</param>
/// <param name="Region">The AWS location this change applies to, or <c>null</c> for every region.</param>
public sealed record AttributeChange(DateTimeOffset At, string Key, string? Value, string? Region);

/// <summary>The product fields that pick a price.</summary>
internal sealed record Variant(string OperatingSystem, string Tenancy, string LicenseModel, string PreInstalledSw, string Capacitystatus);

internal sealed record ReservedTerm(string LeaseContractLength, string OfferingClass, string PurchaseOption);
