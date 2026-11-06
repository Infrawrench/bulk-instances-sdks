using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// Oracle Cloud's compute pricing data, keyed by shape (<c>VM.Standard.E5.Flex-2-16</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what Oracle Cloud's data holds.
/// </summary>
public sealed class OraclePricingData : AwsPricingData
{
    internal OraclePricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The shape with this name, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="shape">e.g. <c>VM.Standard.E5.Flex-2-16</c>.</param>
    public new OracleInstance? Get(string shape) => (OracleInstance?)base.Get(shape);

    /// <summary>Gets the shape with this name, if the bundle has ever listed it.</summary>
    /// <param name="shape">e.g. <c>VM.Standard.E5.Flex-2-16</c>.</param>
    /// <param name="instance">The shape, or <c>null</c> when this returns false.</param>
    public bool TryGet(string shape, [NotNullWhen(true)] out OracleInstance? instance)
    {
        var found = base.TryGet(shape, out var i);
        instance = (OracleInstance?)i;
        return found;
    }

    private protected override OracleInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One Oracle Cloud compute shape. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class OracleInstance : AwsInstance
{
    internal OracleInstance(string name, JsonElement raw, OraclePricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadOraclePricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record OraclePricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when Oracle Cloud's compute pricing data cannot be downloaded. <see
/// cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class OraclePricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public OraclePricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
