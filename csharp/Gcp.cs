using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// Google Cloud's Compute Engine pricing data, keyed by machine type (<c>n2-standard-2</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what Google Cloud's data holds.
/// </summary>
public sealed class GcpPricingData : AwsPricingData
{
    internal GcpPricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The machine type with this name, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="machineType">e.g. <c>n2-standard-2</c>.</param>
    public new GcpInstance? Get(string machineType) => (GcpInstance?)base.Get(machineType);

    /// <summary>Gets the machine type with this name, if the bundle has ever listed it.</summary>
    /// <param name="machineType">e.g. <c>n2-standard-2</c>.</param>
    /// <param name="instance">The machine type, or <c>null</c> when this returns false.</param>
    public bool TryGet(string machineType, [NotNullWhen(true)] out GcpInstance? instance)
    {
        var found = base.TryGet(machineType, out var i);
        instance = (GcpInstance?)i;
        return found;
    }

    private protected override GcpInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One Google Cloud Compute Engine machine type. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class GcpInstance : AwsInstance
{
    internal GcpInstance(string name, JsonElement raw, GcpPricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadGcpPricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record GcpPricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when Google Cloud's pricing data cannot be downloaded. <see cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class GcpPricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public GcpPricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
