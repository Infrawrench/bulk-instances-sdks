namespace Infrawrench.BulkInstances;

/// <summary>Options for <see cref="BulkInstances.DownloadAwsPricingDataAsync"/> and <see cref="BulkInstances.DownloadAwsEc2PricingDataAsync"/>.</summary>
public sealed record AwsPricingDataOptions
{
    /// <summary>Defines your Infrawrench API token. Defaults to the <c>INFRAWRENCH_API_KEY</c> environment variable.</summary>
    public string? Token { get; init; }

    /// <summary>Whether to cache the pricing data. Defaults to true.</summary>
    public bool CachePricingData { get; init; } = true;

    /// <summary>The cache path. Defaults to ~/.infrawrench/aws_pricing_data</summary>
    public string? CachePath { get; init; }

    /// <summary>Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com</summary>
    public string? BaseUrl { get; init; }
}
