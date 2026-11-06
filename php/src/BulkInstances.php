<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

final class BulkInstances
{
    private const DEFAULT_BASE_URL = 'https://instances-bundles.infrawrench.com';
    private const DEFAULT_API_URL = 'https://app.infrawrench.com';
    private const USER_AGENT = 'infrawrench/bulk-instances, php, 1.0';

    /**
     * The AWS platforms Infrawrench publishes a bundle for. Any other lowercase name is
     * requested as is, so a platform added later works without a new SDK.
     */
    public const AWS_PLATFORMS = [
        'ec2', 'rds', 'elasticache', 'opensearch', 'redshift', 'docdb', 'neptune', 'memorydb', 'dax', 'sagemaker', 'emr', 'gamelift', 'spot',
    ];

    /** The variant keys of EC2 bundles, which don't list their own. */
    public const EC2_VARIANT_KEYS = ['operatingSystem', 'tenancy', 'licenseModel', 'preInstalledSw', 'capacitystatus'];

    private function __construct()
    {
    }

    /**
     * Downloads the AWS EC2 pricing data. The same as `downloadAwsPricingData('ec2', ...)`.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws AWSPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadAwsEc2PricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): AWSPricingData {
        return self::downloadAwsPricingData('ec2', $token, $cachePricingData, $cachePath, $baseUrl);
    }

    /**
     * Downloads one AWS platform's pricing data compressed blob and decompresses it.
     *
     * The bucket's `<platform>-latest` object (`latest` for EC2) names the newest bundle. With
     * caching on, a bundle is only downloaded when that names one that is not in the cache yet,
     * and if it cannot be fetched at all (offline, outage) the newest cached bundle is used.
     *
     * @param string $platform One of {@see AWS_PLATFORMS}, e.g. `rds`, or any other lowercase name.
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws AWSPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadAwsPricingData(
        string $platform,
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): AWSPricingData {
        return AWSPricingData::fromJson(self::loadBundle($platform, $token, $cachePricingData, $cachePath, $baseUrl));
    }

    /**
     * Downloads RunPod's pricing data: GPU types (priced per GPU per hour) and CPU pods (per pod per hour).
     * Caching and the offline fallback work as for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws RunpodPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadRunpodPricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): RunpodPricingData {
        return RunpodPricingData::fromJson(
            self::loadBundleAs('runpod', RunpodPricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Downloads Alibaba Cloud's ECS pricing data: pay-as-you-go, subscription and reserved instance prices per
     * region. Caching and the offline fallback work as for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws AlibabaPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadAlibabaPricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): AlibabaPricingData {
        return AlibabaPricingData::fromJson(
            self::loadBundleAs('alibaba', AlibabaPricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Downloads Azure's virtual machine pricing data: pay-as-you-go, Spot and Low Priority prices, reservations and
     * savings plans per region. Caching and the offline fallback work as for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws AzurePricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadAzurePricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): AzurePricingData {
        return AzurePricingData::fromJson(
            self::loadBundleAs('azure', AzurePricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Downloads Google Cloud's Compute Engine pricing data: Standard and Spot prices and committed use discounts per
     * region, for each machine type. Caching and the offline fallback work as for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws GCPPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadGcpPricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): GCPPricingData {
        return GCPPricingData::fromJson(
            self::loadBundleAs('gcp', GCPPricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Downloads Hetzner's cloud server pricing data: hourly prices and monthly caps per location, for each server
     * type. Caching and the offline fallback work as for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws HetznerPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadHetznerPricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): HetznerPricingData {
        return HetznerPricingData::fromJson(
            self::loadBundleAs('hetzner', HetznerPricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Downloads Hetzner's Server Auction pricing data: the hourly price and monthly cap of each server for sale,
     * by listing id. Caching and the offline fallback work as for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws HetznerAuctionPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadHetznerAuctionPricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): HetznerAuctionPricingData {
        return HetznerAuctionPricingData::fromJson(
            self::loadBundleAs('hetznerauction', HetznerAuctionPricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Downloads OVHcloud's Public Cloud pricing data: hourly and monthly prices per pricing zone, for each
     * instance flavor. Caching and the offline fallback work as for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws OVHPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadOvhPricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): OVHPricingData {
        return OVHPricingData::fromJson(
            self::loadBundleAs('ovh', OVHPricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Downloads OVHcloud's eco dedicated server pricing data: monthly rent and prepaid prices per data center and
     * configuration, for Kimsufi, So you Start, Rise and Advance servers. Caching and the offline fallback work as
     * for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws OVHEcoPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadOvhEcoPricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): OVHEcoPricingData {
        return OVHEcoPricingData::fromJson(
            self::loadBundleAs('ovheco', OVHEcoPricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Downloads Oracle Cloud's compute pricing data: hourly prices for each VM and bare metal shape, the same in
     * every commercial region. Caching and the offline fallback work as for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws OraclePricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadOraclePricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): OraclePricingData {
        return OraclePricingData::fromJson(
            self::loadBundleAs('oracle', OraclePricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Downloads IBM Cloud's Virtual Server for VPC pricing data: on-demand, Spot, burstable and reserved prices
     * per region, for each profile. Caching and the offline fallback work as for {@see downloadAwsPricingData()}.
     *
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param bool $cachePricingData Whether to cache the pricing data. Defaults to true.
     * @param string|null $cachePath The cache path. Defaults to ~/.infrawrench/aws_pricing_data
     * @param string|null $baseUrl Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
     *
     * @throws IBMPricingDataException
     * @throws \JsonException if the bundle is not valid
     * @throws \RuntimeException if the cache directory cannot be written
     */
    public static function downloadIbmPricingData(
        ?string $token = null,
        bool $cachePricingData = true,
        ?string $cachePath = null,
        ?string $baseUrl = null,
    ): IBMPricingData {
        return IBMPricingData::fromJson(
            self::loadBundleAs('ibm', IBMPricingDataException::class, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * {@see loadBundle()}, failing with the provider's own exception class.
     *
     * @param
     * class-string<RunpodPricingDataException|AlibabaPricingDataException|AzurePricingDataException|GCPPricingDataException|HetznerPricingDataException|HetznerAuctionPricingDataException|OVHPricingDataException|OVHEcoPricingDataException|OraclePricingDataException|IBMPricingDataException>
     * $exception
     *
     * @throws AWSPricingDataException of class `$exception`
     */
    private static function loadBundleAs(
        string $platform,
        string $exception,
        ?string $token,
        bool $cachePricingData,
        ?string $cachePath,
        ?string $baseUrl,
    ): string {
        return self::withProviderException(
            $exception,
            static fn (): string => self::loadBundle($platform, $token, $cachePricingData, $cachePath, $baseUrl),
        );
    }

    /**
     * Runs `$run`, turning an {@see AWSPricingDataException} into the provider's own exception class.
     *
     * @template T
     *
     * @param class-string<RunpodPricingDataException|AlibabaPricingDataException> $exception
     * @param \Closure(): T $run
     *
     * @return T
     *
     * @throws AWSPricingDataException of class `$exception`
     */
    private static function withProviderException(string $exception, \Closure $run): mixed
    {
        try {
            return $run();
        } catch (AWSPricingDataException $err) {
            throw new $exception($err->getMessage(), $err->status, $err);
        }
    }

    /**
     * Downloads (or reads from the cache) one platform's bundle.
     *
     * @return string The bundle's JSON.
     *
     * @throws AWSPricingDataException
     * @throws \RuntimeException if the cache directory cannot be written
     */
    private static function loadBundle(
        string $platform,
        ?string $token,
        bool $cachePricingData,
        ?string $cachePath,
        ?string $baseUrl,
    ): string {
        if (preg_match('/^[a-z0-9]+$/D', $platform) !== 1) {
            throw new AWSPricingDataException("\"$platform\" is not a platform name.");
        }
        // EC2's keys have no prefix because they were published before the other platforms.
        $prefix = $platform === 'ec2' ? '' : "$platform-";
        $token ??= getenv('INFRAWRENCH_API_KEY') ?: null;
        if ($token === null || $token === '') {
            throw new AWSPricingDataException('No Infrawrench API token: pass `$token` or set INFRAWRENCH_API_KEY.');
        }
        $baseUrl = rtrim($baseUrl ?? self::DEFAULT_BASE_URL, '/');
        $cache = $cachePricingData;
        $cachePath ??= self::homeDir() . DIRECTORY_SEPARATOR . '.infrawrench' . DIRECTORY_SEPARATOR . 'aws_pricing_data';

        try {
            $latest = trim(self::download("$baseUrl/{$prefix}latest", $token), " \t\n\r\v\f");
            if (preg_match('/^[A-Za-z0-9._-]+$/D', $latest) !== 1) {
                throw new AWSPricingDataException("{$prefix}latest holds \"$latest\", which is not a timestamp.");
            }
            $name = "{$prefix}bundle-$latest.json";
        } catch (\Exception $err) {
            // A rejected token is a real answer; anything else falls back to what we already have.
            $rejected = $err instanceof AWSPricingDataException && $err->status === 401;
            $cached = $cache && !$rejected ? self::newestCached($cachePath, $prefix) : null;
            if ($cached === null) {
                throw $err;
            }
            $name = $cached;
        }

        // The cache holds the decompressed JSON: xz decompression is most of a load, reading the file is not.
        $json = null;
        $file = $cachePath . DIRECTORY_SEPARATOR . $name;
        if ($cache && is_file($file)) {
            $json = @file_get_contents($file);
            if ($json === false) {
                $json = null;
            }
        }
        if ($json === null) {
            $json = self::xzDecompress(self::download("$baseUrl/$name.xz", $token));
            if ($cache) {
                self::writeCache($cachePath, $prefix, $name, $json);
            }
        }

        return $json;
    }

    /**
     * Fetches one instance from the Infrawrench API, without downloading the platform's bundle.
     * Nothing is cached.
     *
     * The result is the same as `downloadAwsPricingData($platform)->get($instanceType)`, from
     * whichever bundle the API last synced, which can trail the newest bundle by up to half an hour.
     *
     * @param string $platform One of {@see AWS_PLATFORMS}, e.g. `rds`, or any other lowercase name.
     * @param string $instanceType The instance type, e.g. `m5.large`.
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param string|null $baseUrl Where the Infrawrench API is served from. Defaults to https://app.infrawrench.com
     *
     * @return AWSInstance|null `null` if the platform has no instance with that name.
     *
     * @throws AWSPricingDataException
     * @throws \JsonException if the response is not valid JSON
     */
    public static function fetchAwsInstance(
        string $platform,
        string $instanceType,
        ?string $token = null,
        ?string $baseUrl = null,
    ): ?AWSInstance {
        return self::fetchInstance($platform, $instanceType, $token, $baseUrl, AWSPricingData::class);
    }

    /**
     * Fetches one RunPod GPU type or CPU pod from the Infrawrench API, without downloading RunPod's bundle.
     * Nothing is cached. It takes the same options as {@see fetchAwsInstance()}.
     *
     * The result is the same as `downloadRunpodPricingData()->get($id)`, from whichever bundle the API last
     * synced, which can trail the newest bundle by up to half an hour.
     *
     * @param string $id The GPU type id (`NVIDIA H100 80GB HBM3`) or CPU pod id (`cpu3c-2-4`).
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param string|null $baseUrl Where the Infrawrench API is served from. Defaults to https://app.infrawrench.com
     *
     * @return RunpodInstance|null `null` if RunPod has no instance with that id.
     *
     * @throws RunpodPricingDataException
     * @throws \JsonException if the response is not valid JSON
     */
    public static function fetchRunpodInstance(string $id, ?string $token = null, ?string $baseUrl = null): ?RunpodInstance
    {
        $instance = self::withProviderException(
            RunpodPricingDataException::class,
            static fn (): ?AWSInstance => self::fetchInstance('runpod', $id, $token, $baseUrl, RunpodPricingData::class),
        );
        assert($instance === null || $instance instanceof RunpodInstance);
        return $instance;
    }

    /**
     * Fetches one Alibaba Cloud ECS instance type from the Infrawrench API, without downloading Alibaba's
     * bundle. Nothing is cached. It takes the same options as {@see fetchAwsInstance()}.
     *
     * The result is the same as `downloadAlibabaPricingData()->get($instanceType)`, from whichever bundle the
     * API last synced, which can trail the newest bundle by up to half an hour.
     *
     * @param string $instanceType The instance type, e.g. `ecs.g6.large`.
     * @param string|null $token Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
     * @param string|null $baseUrl Where the Infrawrench API is served from. Defaults to https://app.infrawrench.com
     *
     * @return AlibabaInstance|null `null` if Alibaba has no instance type with that name.
     *
     * @throws AlibabaPricingDataException
     * @throws \JsonException if the response is not valid JSON
     */
    public static function fetchAlibabaInstance(
        string $instanceType,
        ?string $token = null,
        ?string $baseUrl = null,
    ): ?AlibabaInstance {
        $instance = self::withProviderException(
            AlibabaPricingDataException::class,
            static fn (): ?AWSInstance => self::fetchInstance('alibaba', $instanceType, $token, $baseUrl, AlibabaPricingData::class),
        );
        assert($instance === null || $instance instanceof AlibabaInstance);
        return $instance;
    }

    /**
     * GETs one instance from the Infrawrench API and decodes it with `$dataClass`, whose `get()` gives the
     * provider's instance class.
     *
     * @param class-string<AWSPricingData> $dataClass
     *
     * @throws AWSPricingDataException
     * @throws \JsonException if the response is not valid JSON
     */
    private static function fetchInstance(
        string $platform,
        string $instanceType,
        ?string $token,
        ?string $baseUrl,
        string $dataClass,
    ): ?AWSInstance {
        if (preg_match('/^[a-z0-9]+$/D', $platform) !== 1) {
            throw new AWSPricingDataException("\"$platform\" is not a platform name.");
        }
        if ($instanceType === '') {
            throw new AWSPricingDataException('The instance type is empty.');
        }
        $token ??= getenv('INFRAWRENCH_API_KEY') ?: null;
        if ($token === null || $token === '') {
            throw new AWSPricingDataException('No Infrawrench API token: pass `$token` or set INFRAWRENCH_API_KEY.');
        }
        $baseUrl = rtrim($baseUrl ?? self::DEFAULT_API_URL, '/');

        try {
            $json = self::download("$baseUrl/api/v1/aws-bulk-pricing/$platform/" . rawurlencode($instanceType), $token);
        } catch (AWSPricingDataException $err) {
            if ($err->status === 404) {
                return null;
            }
            throw $err;
        }

        // The bundle's tables cut down to what this instance uses, and its row renumbered to match.
        /** @var array{offer: string, compression_table: list<string>, regions: list<array{int, list<array{int, int}>}>, variant_keys: list<string>, variants: list<list<int>>, reserved_terms: list<list<int>>, name: string, instance: mixed} $value */
        $value = json_decode($json, true, 512, JSON_THROW_ON_ERROR);
        /** @var AWSPricingData::BundleFile $raw */
        $raw = [
            'offer' => $value['offer'],
            'compression_table' => $value['compression_table'],
            'snapshots' => [],
            'regions' => $value['regions'],
            'variant_keys' => $value['variant_keys'],
            'variants' => $value['variants'],
            'reserved_terms' => $value['reserved_terms'],
            'instances' => [$value['name'] => $value['instance']],
        ];
        return (new $dataClass($raw))->get($value['name']);
    }

    /**
     * GETs `url`, retrying the 503 the bundles Worker answers when it cannot reach the Infrawrench API
     * (and the API answers when it cannot reach its store).
     */
    private static function download(string $url, string $token): string
    {
        for ($attempt = 1; ; $attempt++) {
            [$status, $body, $retryAfter] = self::get($url, $token);
            if ($status >= 200 && $status < 300) {
                return $body;
            }
            if ($status === 401) {
                throw new AWSPricingDataException('The Infrawrench API did not accept the token (unknown, revoked or expired).', 401);
            }
            if ($status !== 503 || $attempt === 3) {
                throw new AWSPricingDataException("GET $url failed with status $status.", $status);
            }
            $seconds = is_numeric($retryAfter) ? (float) $retryAfter : 0.0;
            usleep((int) (min(max($seconds ?: 5.0, 0.0), 86400.0) * 1_000_000));
        }
    }

    /** @return array{int, string, ?string} The status, the body and the `Retry-After` header. */
    private static function get(string $url, string $token): array
    {
        $retryAfter = null;
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_ENCODING => '',
            CURLOPT_CONNECTTIMEOUT => 30,
            CURLOPT_HTTPHEADER => [
                "Authorization: Bearer $token",
                'User-Agent: ' . self::USER_AGENT,
            ],
            CURLOPT_HEADERFUNCTION => static function (\CurlHandle $ch, string $line) use (&$retryAfter): int {
                if (str_starts_with($line, 'HTTP/')) {
                    $retryAfter = null; // A new response after a redirect.
                } elseif (stripos($line, 'retry-after:') === 0) {
                    $retryAfter = trim(substr($line, strlen('retry-after:')));
                }
                return strlen($line);
            },
        ]);
        $body = curl_exec($ch);
        if (!is_string($body)) {
            throw new AWSPricingDataException(
                "GET $url failed: " . curl_error($ch),
                null,
                new \RuntimeException(curl_error($ch), curl_errno($ch)),
            );
        }
        return [curl_getinfo($ch, CURLINFO_RESPONSE_CODE), $body, $retryAfter];
    }

    /** The newest bundle for a platform already in the cache directory, if any. */
    private static function newestCached(string $cachePath, string $prefix): ?string
    {
        $files = array_values(array_filter(
            @scandir($cachePath) ?: [],
            static fn (string $f) => self::isBundle($f, $prefix, '/^bundle-.+\.json$/D'),
        ));
        sort($files, SORT_STRING);
        return $files === [] ? null : $files[count($files) - 1];
    }

    private static function writeCache(string $cachePath, string $prefix, string $name, string $json): void
    {
        if (!is_dir($cachePath) && !@mkdir($cachePath, 0777, true) && !is_dir($cachePath)) {
            throw new \RuntimeException("Cannot create the cache directory $cachePath: " . self::lastError());
        }
        // Write then rename, so a crash mid-write never leaves a truncated bundle to be read next time.
        $tmp = $cachePath . DIRECTORY_SEPARATOR . $name . '.' . getmypid() . '.tmp';
        if (@file_put_contents($tmp, $json) !== strlen($json) || !@rename($tmp, $cachePath . DIRECTORY_SEPARATOR . $name)) {
            $error = self::lastError();
            @unlink($tmp);
            throw new \RuntimeException("Cannot write $name to the cache directory $cachePath: $error");
        }
        // This platform's older bundles, including compressed ones cached by earlier versions of this SDK.
        foreach (@scandir($cachePath) ?: [] as $f) {
            if ($f !== $name && self::isBundle($f, $prefix, '/^bundle-.+\.json(\.xz)?$/D')) {
                $path = $cachePath . DIRECTORY_SEPARATOR . $f;
                if (!@unlink($path) && file_exists($path)) {
                    throw new \RuntimeException("Cannot delete $path: " . self::lastError());
                }
            }
        }
    }

    /** Whether `$f` is `$prefix` followed by a name matching `$pattern`. */
    private static function isBundle(string $f, string $prefix, string $pattern): bool
    {
        return str_starts_with($f, $prefix) && preg_match($pattern, substr($f, strlen($prefix))) === 1;
    }

    /**
     * Decompresses with ext-xz when it is loaded, otherwise through the `xz` binary.
     *
     * @throws AWSPricingDataException if neither is available, or the data is not valid xz
     */
    private static function xzDecompress(string $data): string
    {
        if (function_exists('xzdecode')) {
            $out = xzdecode($data);
            if (!is_string($out)) {
                throw new AWSPricingDataException('The bundle is not valid xz data.');
            }
            return $out;
        }

        $xz = self::findXzBinary();
        if ($xz === null) {
            throw new AWSPricingDataException(
                'Cannot decompress the bundle: install the xz PECL extension, or the xz command (xz-utils) on the PATH.',
            );
        }
        // Feed xz from a file rather than a pipe, so it can never block writing while we block reading.
        $in = tmpfile();
        $err = tmpfile();
        if ($in === false || $err === false || fwrite($in, $data) !== strlen($data) || !rewind($in)) {
            throw new \RuntimeException('Cannot write a temporary file: ' . self::lastError());
        }
        $proc = proc_open([$xz, '-dc'], [0 => $in, 1 => ['pipe', 'w'], 2 => $err], $pipes);
        if ($proc === false) {
            throw new AWSPricingDataException("Cannot run $xz: " . self::lastError());
        }
        $out = stream_get_contents($pipes[1]);
        fclose($pipes[1]);
        $code = proc_close($proc);
        fclose($in);
        if ($code !== 0 || !is_string($out)) {
            rewind($err);
            $message = trim((string) stream_get_contents($err));
            throw new AWSPricingDataException("xz failed to decompress the bundle (exit $code)" . ($message === '' ? '.' : ": $message"));
        }
        return $out;
    }

    private static function findXzBinary(): ?string
    {
        $names = PHP_OS_FAMILY === 'Windows' ? ['xz.exe'] : ['xz'];
        foreach (explode(PATH_SEPARATOR, getenv('PATH') ?: '') as $dir) {
            foreach ($names as $n) {
                $path = $dir . DIRECTORY_SEPARATOR . $n;
                if ($dir !== '' && is_file($path) && is_executable($path)) {
                    return $path;
                }
            }
        }
        return null;
    }

    private static function homeDir(): string
    {
        $home = getenv('HOME') ?: getenv('USERPROFILE') ?: null;
        if ($home === null && function_exists('posix_getpwuid')) {
            $home = (posix_getpwuid(posix_geteuid()) ?: [])['dir'] ?? null;
        }
        return $home ?? throw new AWSPricingDataException('Cannot find the home directory: pass `$cachePath`.');
    }

    private static function lastError(): string
    {
        return error_get_last()['message'] ?? 'unknown error';
    }
}
