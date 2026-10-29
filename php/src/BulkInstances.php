<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

final class BulkInstances
{
    private const DEFAULT_BASE_URL = 'https://instances-bundles.infrawrench.com';
    private const USER_AGENT = 'infrawrench/bulk-instances, php, 1.0';

    private function __construct()
    {
    }

    /**
     * Downloads the AWS EC2 pricing data compressed blob and decompresses it.
     *
     * The bucket's `latest` object names the newest bundle. With caching on, a bundle
     * is only downloaded when `latest` names one that is not in the cache yet, and if
     * `latest` cannot be fetched at all (offline, outage) the newest cached bundle is used.
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
        $token ??= getenv('INFRAWRENCH_API_KEY') ?: null;
        if ($token === null || $token === '') {
            throw new AWSPricingDataException('No Infrawrench API token: pass `$token` or set INFRAWRENCH_API_KEY.');
        }
        $baseUrl = rtrim($baseUrl ?? self::DEFAULT_BASE_URL, '/');
        $cache = $cachePricingData;
        $cachePath ??= self::homeDir() . DIRECTORY_SEPARATOR . '.infrawrench' . DIRECTORY_SEPARATOR . 'aws_pricing_data';

        try {
            $latest = trim(self::download("$baseUrl/latest", $token), " \t\n\r\v\f");
            if (preg_match('/^[A-Za-z0-9._-]+$/D', $latest) !== 1) {
                throw new AWSPricingDataException("latest holds \"$latest\", which is not a timestamp.");
            }
            $name = "bundle-$latest.json";
        } catch (\Exception $err) {
            // A rejected token is a real answer; anything else falls back to what we already have.
            $rejected = $err instanceof AWSPricingDataException && $err->status === 401;
            $cached = $cache && !$rejected ? self::newestCached($cachePath) : null;
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
                self::writeCache($cachePath, $name, $json);
            }
        }

        return AWSPricingData::fromJson($json);
    }

    /** GETs `url`, retrying the 503 the bundles Worker answers when it cannot reach the Infrawrench API. */
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

    /** The newest bundle already in the cache directory, if any. */
    private static function newestCached(string $cachePath): ?string
    {
        $files = array_values(array_filter(
            @scandir($cachePath) ?: [],
            static fn (string $f) => preg_match('/^bundle-.+\.json$/D', $f) === 1,
        ));
        sort($files, SORT_STRING);
        return $files === [] ? null : $files[count($files) - 1];
    }

    private static function writeCache(string $cachePath, string $name, string $json): void
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
        // Older bundles, including compressed ones cached by earlier versions of this SDK.
        foreach (@scandir($cachePath) ?: [] as $f) {
            if ($f !== $name && preg_match('/^bundle-.+\.json(\.xz)?$/D', $f) === 1) {
                $path = $cachePath . DIRECTORY_SEPARATOR . $f;
                if (!@unlink($path) && file_exists($path)) {
                    throw new \RuntimeException("Cannot delete $path: " . self::lastError());
                }
            }
        }
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
