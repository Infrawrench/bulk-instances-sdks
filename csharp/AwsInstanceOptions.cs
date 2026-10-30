namespace Infrawrench.BulkInstances;

/// <summary>Options for <see cref="BulkInstances.FetchAwsInstanceAsync"/>.</summary>
public sealed record AwsInstanceOptions
{
    /// <summary>Defines your Infrawrench API token. Defaults to the <c>INFRAWRENCH_API_KEY</c> environment variable.</summary>
    public string? Token { get; init; }

    /// <summary>Where the Infrawrench API is served from. Defaults to https://app.infrawrench.com</summary>
    public string? BaseUrl { get; init; }
}
