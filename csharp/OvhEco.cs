using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// OVHcloud's eco dedicated server pricing data, keyed by server (<c>24sys01</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what OVHcloud's data holds.
/// </summary>
public sealed class OvhEcoPricingData : AwsPricingData
{
    internal OvhEcoPricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The server with this name, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="server">e.g. <c>24sys01</c>.</param>
    public new OvhEcoInstance? Get(string server) => (OvhEcoInstance?)base.Get(server);

    /// <summary>Gets the server with this name, if the bundle has ever listed it.</summary>
    /// <param name="server">e.g. <c>24sys01</c>.</param>
    /// <param name="instance">The server, or <c>null</c> when this returns false.</param>
    public bool TryGet(string server, [NotNullWhen(true)] out OvhEcoInstance? instance)
    {
        var found = base.TryGet(server, out var i);
        instance = (OvhEcoInstance?)i;
        return found;
    }

    private protected override OvhEcoInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One OVHcloud eco dedicated server. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class OvhEcoInstance : AwsInstance
{
    internal OvhEcoInstance(string name, JsonElement raw, OvhEcoPricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadOvhEcoPricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record OvhEcoPricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when OVHcloud's eco dedicated server pricing data cannot be downloaded. <see
/// cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class OvhEcoPricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public OvhEcoPricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
