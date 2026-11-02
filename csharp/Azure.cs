using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// Azure's virtual machine pricing data, keyed by VM size (<c>Standard_D2s_v3</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what Azure's data holds.
/// </summary>
public sealed class AzurePricingData : AwsPricingData
{
    internal AzurePricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The VM size with this name, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="size">e.g. <c>Standard_D2s_v3</c>.</param>
    public new AzureInstance? Get(string size) => (AzureInstance?)base.Get(size);

    /// <summary>Gets the VM size with this name, if the bundle has ever listed it.</summary>
    /// <param name="size">e.g. <c>Standard_D2s_v3</c>.</param>
    /// <param name="instance">The VM size, or <c>null</c> when this returns false.</param>
    public bool TryGet(string size, [NotNullWhen(true)] out AzureInstance? instance)
    {
        var found = base.TryGet(size, out var i);
        instance = (AzureInstance?)i;
        return found;
    }

    private protected override AzureInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One Azure virtual machine size. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class AzureInstance : AwsInstance
{
    internal AzureInstance(string name, JsonElement raw, AzurePricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadAzurePricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record AzurePricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when Azure's pricing data cannot be downloaded. <see cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class AzurePricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public AzurePricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
