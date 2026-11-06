using System;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;

namespace Infrawrench.BulkInstances;

/// <summary>
/// Hetzner's Server Auction pricing data, keyed by listing (<c>3107671</c>).
/// It decodes the same way as <see cref="AwsPricingData"/>; see the README for what Hetzner's data holds.
/// </summary>
public sealed class HetznerAuctionPricingData : AwsPricingData
{
    internal HetznerAuctionPricingData(byte[] utf8Json)
        : base(utf8Json)
    {
    }

    /// <summary>The listing with this name, or <c>null</c> if the bundle has never listed it.</summary>
    /// <param name="listingId">e.g. <c>3107671</c>.</param>
    public new HetznerAuctionInstance? Get(string listingId) => (HetznerAuctionInstance?)base.Get(listingId);

    /// <summary>Gets the listing with this name, if the bundle has ever listed it.</summary>
    /// <param name="listingId">e.g. <c>3107671</c>.</param>
    /// <param name="instance">The listing, or <c>null</c> when this returns false.</param>
    public bool TryGet(string listingId, [NotNullWhen(true)] out HetznerAuctionInstance? instance)
    {
        var found = base.TryGet(listingId, out var i);
        instance = (HetznerAuctionInstance?)i;
        return found;
    }

    private protected override HetznerAuctionInstance NewInstance(string name, JsonElement raw) => new(name, raw, this);
}

/// <summary>One Hetzner Server Auction listing. It has the same members as <see cref="AwsInstance"/>, which it extends.</summary>
public sealed class HetznerAuctionInstance : AwsInstance
{
    internal HetznerAuctionInstance(string name, JsonElement raw, HetznerAuctionPricingData data)
        : base(name, raw, data)
    {
    }
}

/// <summary>Options for <see cref="BulkInstances.DownloadHetznerAuctionPricingDataAsync"/>: the same as for the AWS platforms.</summary>
public sealed record HetznerAuctionPricingDataOptions : AwsPricingDataOptions;

/// <summary>
/// Thrown when Hetzner's Server Auction pricing data cannot be downloaded. <see
/// cref="AwsPricingDataException.Status"/> is the HTTP
/// status, if there was a response.
/// </summary>
public sealed class HetznerAuctionPricingDataException : AwsPricingDataException
{
    /// <summary>Creates the exception.</summary>
    /// <param name="message">What went wrong.</param>
    /// <param name="status">The HTTP status, if there was a response.</param>
    /// <param name="innerException">The underlying failure, e.g. the transport error.</param>
    public HetznerAuctionPricingDataException(string message, int? status = null, Exception? innerException = null)
        : base(message, status, innerException)
    {
    }
}
