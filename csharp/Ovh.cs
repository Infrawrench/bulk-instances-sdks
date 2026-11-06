using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// OVHcloud's Public Cloud pricing data, keyed by flavor (<c>b3-8</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what OVHcloud's data holds.
/// </summary>
public sealed class OvhPricingData : AwsPricingData
{
    internal OvhPricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The flavor with this name, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="flavor">e.g. <c>b3-8</c>.</param>
    public new OvhInstance? Get(string flavor) => (OvhInstance?)base.Get(flavor);

    /// <summary>Gets the flavor with this name, if the bundle has ever listed it.</summary>
    /// <param name="flavor">e.g. <c>b3-8</c>.</param>
    /// <param name="instance">The flavor, or <c>null</c> when this returns false.</param>
    public bool TryGet(string flavor, [NotNullWhen(true)] out OvhInstance? instance)
    {
        var found = base.TryGet(flavor, out var i);
        instance = (OvhInstance?)i;
        return found;
    }

    private protected override OvhInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One OVHcloud Public Cloud flavor. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class OvhInstance : AwsInstance
{
    internal OvhInstance(string name, JsonElement raw, OvhPricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadOvhPricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record OvhPricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when OVHcloud's Public Cloud pricing data cannot be downloaded. <see
/// cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class OvhPricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public OvhPricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
