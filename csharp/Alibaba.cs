using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// Alibaba Cloud's ECS pricing data, keyed by instance type (<c>ecs.g6.large</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what Alibaba's data holds.
/// </summary>
public sealed class AlibabaPricingData : AwsPricingData
{
    internal AlibabaPricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The instance type with this name, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="instanceType">e.g. <c>ecs.g6.large</c>.</param>
    public new AlibabaInstance? Get(string instanceType) => (AlibabaInstance?)base.Get(instanceType);

    /// <summary>Gets the instance type with this name, if the bundle has ever listed it.</summary>
    /// <param name="instanceType">e.g. <c>ecs.g6.large</c>.</param>
    /// <param name="instance">The instance type, or <c>null</c> when this returns false.</param>
    public bool TryGet(string instanceType, [NotNullWhen(true)] out AlibabaInstance? instance)
    {
        var found = base.TryGet(instanceType, out var i);
        instance = (AlibabaInstance?)i;
        return found;
    }

    private protected override AlibabaInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One Alibaba Cloud ECS instance type. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class AlibabaInstance : AwsInstance
{
    internal AlibabaInstance(string name, JsonElement raw, AlibabaPricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadAlibabaPricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record AlibabaPricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when Alibaba Cloud's pricing data cannot be downloaded. <see cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class AlibabaPricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public AlibabaPricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
