using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using SharpCompress.Compressors.Xz;

namespace Infrawrench.BulkInstances;

/// <summary>Downloads the Infrawrench AWS pricing bundles: EC2 and the other AWS platforms.</summary>
public static class BulkInstances
{
    private const string DefaultBaseUrl = "https://instances-bundles.infrawrench.com";
    private const string UserAgent = "infrawrench/bulk-instances, csharp, 1.0";

    private static readonly HttpClient Http = new(new SocketsHttpHandler
    {
        ConnectTimeout = TimeSpan.FromSeconds(10),
        PooledConnectionLifetime = TimeSpan.FromMinutes(5),
    })
    {
        Timeout = Timeout.InfiniteTimeSpan,
    };

    private static readonly Regex PlatformPattern = new(@"^[a-z0-9]+\z", RegexOptions.CultureInvariant);
    private static readonly Regex LatestPattern = new(@"^[A-Za-z0-9._-]+\z", RegexOptions.CultureInvariant);
    private static readonly Regex BundlePattern = new(@"^bundle-.+\.json\z", RegexOptions.CultureInvariant);
    private static readonly Regex StalePattern = new(@"^bundle-.+\.json(\.xz)?\z", RegexOptions.CultureInvariant);

    /// <summary>
    /// The AWS platforms Infrawrench publishes a bundle for. Any other lowercase name is
    /// requested as is, so a platform added later works without a new SDK.
    /// </summary>
    public static IReadOnlyList<string> AwsPlatforms { get; } = Array.AsReadOnly(new[]
    {
        "ec2", "rds", "elasticache", "opensearch", "redshift", "docdb", "neptune", "memorydb", "dax", "sagemaker", "emr", "gamelift",
    });

    /// <summary>The variant keys of EC2 bundles, which don't list their own.</summary>
    public static IReadOnlyList<string> Ec2VariantKeys { get; } = Array.AsReadOnly(new[]
    {
        "operatingSystem", "tenancy", "licenseModel", "preInstalledSw", "capacitystatus",
    });

    /// <summary>
    /// Downloads the AWS EC2 pricing data. The same as <c>DownloadAwsPricingDataAsync("ec2", options, cancellationToken)</c>.
    /// </summary>
    /// <param name="options">Token, caching and server options; all optional.</param>
    /// <param name="cancellationToken">Cancels the download.</param>
    /// <exception cref="AwsPricingDataException">The token is missing or rejected, or the bundle cannot be downloaded.</exception>
    public static Task<AwsPricingData> DownloadAwsEc2PricingDataAsync(
        AwsPricingDataOptions? options = null, CancellationToken cancellationToken = default) =>
        DownloadAwsPricingDataAsync("ec2", options, cancellationToken);

    /// <summary>
    /// Downloads one AWS platform's pricing data compressed blob and decompresses it.
    /// </summary>
    /// <remarks>
    /// The bucket's <c>&lt;platform&gt;-latest</c> object (<c>latest</c> for EC2) names the newest bundle. With
    /// caching on, a bundle is only downloaded when that names one that is not in the cache yet,
    /// and if it cannot be fetched at all (offline, outage) the newest cached bundle is used.
    /// </remarks>
    /// <param name="platform">e.g. <c>ec2</c> or <c>rds</c>; see <see cref="AwsPlatforms"/>.</param>
    /// <param name="options">Token, caching and server options; all optional.</param>
    /// <param name="cancellationToken">Cancels the download.</param>
    /// <exception cref="AwsPricingDataException">
    /// The platform is not a lowercase name, the token is missing or rejected, or the bundle cannot be downloaded.
    /// </exception>
    public static async Task<AwsPricingData> DownloadAwsPricingDataAsync(
        string platform, AwsPricingDataOptions? options = null, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(platform);
        if (!PlatformPattern.IsMatch(platform))
        {
            throw new AwsPricingDataException($"\"{platform}\" is not a platform name.");
        }
        // EC2's keys have no prefix because they were published before the other platforms.
        var prefix = platform == "ec2" ? "" : $"{platform}-";
        options ??= new AwsPricingDataOptions();
        var token = options.Token ?? Environment.GetEnvironmentVariable("INFRAWRENCH_API_KEY");
        if (string.IsNullOrEmpty(token))
        {
            throw new AwsPricingDataException("No Infrawrench API token: pass `Token` or set INFRAWRENCH_API_KEY.");
        }
        var baseUrl = (options.BaseUrl ?? DefaultBaseUrl).TrimEnd('/');
        var cache = options.CachePricingData;
        var cachePath = options.CachePath
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".infrawrench", "aws_pricing_data");

        string name;
        try
        {
            string latest;
            var latestUrl = $"{baseUrl}/{prefix}latest";
            using (var res = await DownloadAsync(latestUrl, token, cancellationToken).ConfigureAwait(false))
            {
                latest = (await ReadBodyAsync(res, latestUrl, r => r.Content.ReadAsStringAsync(cancellationToken)).ConfigureAwait(false)).Trim();
            }
            if (!LatestPattern.IsMatch(latest))
            {
                throw new AwsPricingDataException($"{prefix}latest holds \"{latest}\", which is not a timestamp.");
            }
            name = $"{prefix}bundle-{latest}.json";
        }
        catch (Exception err) when (!(err is OperationCanceledException && cancellationToken.IsCancellationRequested))
        {
            // A rejected token is a real answer; anything else falls back to what we already have.
            var cached = cache && !(err is AwsPricingDataException { Status: 401 }) ? NewestCached(cachePath, prefix) : null;
            if (cached is null) throw;
            name = cached;
        }

        // The cache holds the decompressed JSON: xz decompression is most of a load, reading the file is not.
        var path = Path.Combine(cachePath, name);
        byte[]? json = null;
        if (cache)
        {
            try
            {
                json = await File.ReadAllBytesAsync(path, cancellationToken).ConfigureAwait(false);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
            }
        }
        if (json is null)
        {
            var url = $"{baseUrl}/{name}.xz";
            byte[] compressed;
            using (var res = await DownloadAsync(url, token, cancellationToken).ConfigureAwait(false))
            {
                compressed = await ReadBodyAsync(res, url, r => r.Content.ReadAsByteArrayAsync(cancellationToken)).ConfigureAwait(false);
            }
            json = Decompress(compressed);
            if (cache)
            {
                Directory.CreateDirectory(cachePath);
                // Write then rename, so a crash mid-write never leaves a truncated bundle to be read next time.
                var tmp = Path.Combine(cachePath, $"{name}.{Environment.ProcessId}.tmp");
                await File.WriteAllBytesAsync(tmp, json, cancellationToken).ConfigureAwait(false);
                File.Move(tmp, path, overwrite: true);
                // This platform's older bundles, including compressed ones cached by earlier versions of this SDK.
                foreach (var f in Directory.GetFileSystemEntries(cachePath).Select(p => Path.GetFileName(p)))
                {
                    if (f != name && IsPlatformFile(f, prefix, StalePattern)) File.Delete(Path.Combine(cachePath, f));
                }
            }
        }

        return new AwsPricingData(json);
    }

    private static byte[] Decompress(byte[] compressed)
    {
        using var xz = new XZStream(new MemoryStream(compressed, writable: false));
        using var output = new MemoryStream();
        xz.CopyTo(output);
        return output.ToArray();
    }

    private static async Task<HttpResponseMessage> SendAsync(string url, string token, CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        request.Headers.TryAddWithoutValidation("Authorization", $"Bearer {token}");
        request.Headers.TryAddWithoutValidation("User-Agent", UserAgent);
        try
        {
            return await Http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception e) when (IsTransportFailure(e, cancellationToken))
        {
            throw new AwsPricingDataException($"GET {url} failed: {e.Message}", null, e);
        }
    }

    private static async Task<T> ReadBodyAsync<T>(HttpResponseMessage res, string url, Func<HttpResponseMessage, Task<T>> read)
    {
        try
        {
            return await read(res).ConfigureAwait(false);
        }
        catch (Exception e) when (e is HttpRequestException or IOException)
        {
            throw new AwsPricingDataException($"GET {url} failed: {e.Message}", null, e);
        }
    }

    private static bool IsTransportFailure(Exception e, CancellationToken cancellationToken) =>
        e is HttpRequestException or IOException
        // HttpClient reports its own timeouts as cancellations.
        || (e is OperationCanceledException && !cancellationToken.IsCancellationRequested);

    /// <summary>GETs <paramref name="url"/>, retrying the 503 the bundles Worker answers when it cannot reach the Infrawrench API.</summary>
    private static async Task<HttpResponseMessage> DownloadAsync(string url, string token, CancellationToken cancellationToken)
    {
        for (var attempt = 1; ; attempt++)
        {
            var res = await SendAsync(url, token, cancellationToken).ConfigureAwait(false);
            if (res.IsSuccessStatusCode) return res;
            var status = (int)res.StatusCode;
            var retryAfter = RetryAfterSeconds(res);
            res.Dispose();
            if (status == 401)
            {
                throw new AwsPricingDataException("The Infrawrench API did not accept the token (unknown, revoked or expired).", 401);
            }
            if (status != 503 || attempt == 3)
            {
                throw new AwsPricingDataException($"GET {url} failed with status {status}.", status);
            }
            await Task.Delay(TimeSpan.FromSeconds(retryAfter), cancellationToken).ConfigureAwait(false);
        }
    }

    /// <summary>The numeric <c>Retry-After</c>, or 5 when it is missing, 0 or not a number.</summary>
    private static double RetryAfterSeconds(HttpResponseMessage res)
    {
        if (res.Headers.NonValidated.TryGetValues("Retry-After", out var values)
            && double.TryParse(values.ToString().Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var seconds)
            && seconds != 0 && double.IsFinite(seconds))
        {
            return Math.Clamp(seconds, 0, int.MaxValue / 1000);
        }
        return 5;
    }

    /// <summary>Whether <paramref name="file"/> is this platform's: its prefix followed by a name <paramref name="pattern"/> matches.</summary>
    private static bool IsPlatformFile(string file, string prefix, Regex pattern) =>
        file.StartsWith(prefix, StringComparison.Ordinal) && pattern.IsMatch(file.AsSpan(prefix.Length));

    /// <summary>The newest bundle for a platform already in the cache directory, if any.</summary>
    private static string? NewestCached(string cachePath, string prefix)
    {
        try
        {
            return Directory.EnumerateFileSystemEntries(cachePath)
                .Select(p => Path.GetFileName(p))
                .Where(f => IsPlatformFile(f, prefix, BundlePattern))
                .OrderBy(f => f, StringComparer.Ordinal)
                .LastOrDefault();
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }
}
