using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// RunPod's pricing data, keyed by GPU type id (<c>NVIDIA H100 80GB HBM3</c>) or CPU pod id (<c>cpu3c-2-4</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what RunPod's data holds.
/// </summary>
public sealed class RunpodPricingData : AwsPricingData
{
    internal RunpodPricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The GPU type or CPU pod with this id, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="id">e.g. <c>NVIDIA H100 80GB HBM3</c> or <c>cpu3c-2-4</c>.</param>
    public new RunpodInstance? Get(string id) => (RunpodInstance?)base.Get(id);

    /// <summary>Gets the GPU type or CPU pod with this id, if the bundle has ever listed it.</summary>
    /// <param name="id">e.g. <c>NVIDIA H100 80GB HBM3</c> or <c>cpu3c-2-4</c>.</param>
    /// <param name="instance">The GPU type or CPU pod, or <c>null</c> when this returns false.</param>
    public bool TryGet(string id, [NotNullWhen(true)] out RunpodInstance? instance)
    {
        var found = base.TryGet(id, out var i);
        instance = (RunpodInstance?)i;
        return found;
    }

    private protected override RunpodInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One RunPod GPU type or CPU pod. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class RunpodInstance : AwsInstance
{
    internal RunpodInstance(string name, JsonElement raw, RunpodPricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadRunpodPricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record RunpodPricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when RunPod's pricing data cannot be downloaded. <see cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class RunpodPricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public RunpodPricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
