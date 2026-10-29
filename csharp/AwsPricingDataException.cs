using System;

namespace Infrawrench.BulkInstances;

/// <summary>
/// Thrown when the pricing data cannot be downloaded. <see cref="Status"/> is the HTTP status, if there was a response.
/// </summary>
public sealed class AwsPricingDataException : Exception
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public AwsPricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, innerException)
    {
        Status = status;
    }

    /// <summary>The HTTP status, or <c>null</c> if there was no response.</summary>
    public int? Status { get; }
}
