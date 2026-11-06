using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// IBM Cloud's Virtual Server for VPC pricing data, keyed by profile (<c>bx3d-2x10</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what IBM Cloud's data holds.
/// </summary>
public sealed class IbmPricingData : AwsPricingData
{
    internal IbmPricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The profile with this name, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="profile">e.g. <c>bx3d-2x10</c>.</param>
    public new IbmInstance? Get(string profile) => (IbmInstance?)base.Get(profile);

    /// <summary>Gets the profile with this name, if the bundle has ever listed it.</summary>
    /// <param name="profile">e.g. <c>bx3d-2x10</c>.</param>
    /// <param name="instance">The profile, or <c>null</c> when this returns false.</param>
    public bool TryGet(string profile, [NotNullWhen(true)] out IbmInstance? instance)
    {
        var found = base.TryGet(profile, out var i);
        instance = (IbmInstance?)i;
        return found;
    }

    private protected override IbmInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One IBM Cloud Virtual Server for VPC profile. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class IbmInstance : AwsInstance
{
    internal IbmInstance(string name, JsonElement raw, IbmPricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadIbmPricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record IbmPricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when IBM Cloud's Virtual Server for VPC pricing data cannot be downloaded. <see
/// cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class IbmPricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public IbmPricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
