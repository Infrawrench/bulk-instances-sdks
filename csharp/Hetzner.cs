using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// Hetzner's cloud server pricing data, keyed by server type (<c>cx23</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what Hetzner's data holds.
/// </summary>
public sealed class HetznerPricingData : AwsPricingData
{
    internal HetznerPricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The server type with this name, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="serverType">e.g. <c>cx23</c>.</param>
    public new HetznerInstance? Get(string serverType) => (HetznerInstance?)base.Get(serverType);

    /// <summary>Gets the server type with this name, if the bundle has ever listed it.</summary>
    /// <param name="serverType">e.g. <c>cx23</c>.</param>
    /// <param name="instance">The server type, or <c>null</c> when this returns false.</param>
    public bool TryGet(string serverType, [NotNullWhen(true)] out HetznerInstance? instance)
    {
        var found = base.TryGet(serverType, out var i);
        instance = (HetznerInstance?)i;
        return found;
    }

    private protected override HetznerInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One Hetzner cloud server type. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class HetznerInstance : AwsInstance
{
    internal HetznerInstance(string name, JsonElement raw, HetznerPricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadHetznerPricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record HetznerPricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when Hetzner's cloud server pricing data cannot be downloaded. <see
/// cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class HetznerPricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public HetznerPricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
