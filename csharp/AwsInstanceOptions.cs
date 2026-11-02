namespace Infrawrench.BulkInstances;

/// <summary>Options for <see cref="BulkInstances.FetchAwsInstanceAsync"/>.</summary>
/// <remarks>
/// RunPod's and Alibaba Cloud's methods take the subclasses <see cref="RunpodInstanceOptions"/> and
/// <see cref="AlibabaInstanceOptions"/>, which have the same options.
/// </remarks>
public record AwsInstanceOptions
{
    /// <summary>Defines your Infrawrench API token. Defaults to the <c>INFRAWRENCH_API_KEY</c> environment variable.</summary>
    public string? Token { get; init; }

    /// <summary>Where the Infrawrench API is served from. Defaults to https://app.infrawrench.com</summary>
    public string? BaseUrl { get; init; }
}
