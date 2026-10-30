package com.infrawrench.bulkinstances;

import java.io.BufferedInputStream;
import java.io.FilterInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryIteratorException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Duration;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;
import org.tukaani.xz.XZInputStream;

/** Downloads AWS pricing data: EC2's, or any other platform's. */
public final class BulkInstances {
    /**
     * The AWS platforms Infrawrench publishes a bundle for. Any other lowercase name is requested as is, so a
     * platform added later works without a new SDK.
     */
    public static final List<String> AWS_PLATFORMS = List.of(
            "ec2", "rds", "elasticache", "opensearch", "redshift", "docdb", "neptune", "memorydb", "dax", "sagemaker",
            "emr", "gamelift");

    /** The variant keys of EC2 bundles, which don't list their own. */
    public static final List<String> EC2_VARIANT_KEYS =
            List.of("operatingSystem", "tenancy", "licenseModel", "preInstalledSw", "capacitystatus");

    private static final String USER_AGENT = "infrawrench/bulk-instances, java, 1.0";
    private static final Pattern PLATFORM = Pattern.compile("[a-z0-9]+");
    private static final Pattern LATEST = Pattern.compile("[A-Za-z0-9._-]+");
    private static final Pattern BUNDLE = Pattern.compile("bundle-.+\\.json");
    private static final Pattern OLD_BUNDLE = Pattern.compile("bundle-.+\\.json(\\.xz)?");
    private static final Pattern RETRY_AFTER = Pattern.compile("[+-]?(\\d+\\.?\\d*|\\.\\d+)([eE][+-]?\\d+)?");

    private BulkInstances() {}

    /** Created on first use; the same timeouts as Node's fetch. */
    private static final class Http {
        static final HttpClient CLIENT = HttpClient.newBuilder()
                .followRedirects(HttpClient.Redirect.NORMAL)
                .connectTimeout(Duration.ofSeconds(10))
                .build();
    }

    /**
     * Downloads the AWS EC2 pricing data with the default options.
     *
     * @return the pricing data
     * @throws AWSPricingDataException if the pricing data cannot be downloaded
     * @throws IOException if the cache cannot be read or written, or the bundle is corrupt
     * @see #downloadAwsEc2PricingData(AWSPricingDataOptions)
     */
    public static AWSPricingData downloadAwsEc2PricingData() throws IOException {
        return downloadAwsEc2PricingData(AWSPricingDataOptions.builder().build());
    }

    /**
     * Downloads the AWS EC2 pricing data. The same as {@code downloadAwsPricingData("ec2", options)}.
     *
     * @param options the options
     * @return the pricing data
     * @throws AWSPricingDataException if the pricing data cannot be downloaded
     * @throws IOException if the cache cannot be read or written, or the bundle is corrupt
     *     ({@link InterruptedIOException} if the thread is interrupted)
     * @see #downloadAwsPricingData(String, AWSPricingDataOptions)
     */
    public static AWSPricingData downloadAwsEc2PricingData(AWSPricingDataOptions options) throws IOException {
        return downloadAwsPricingData("ec2", options);
    }

    /**
     * Downloads one AWS platform's pricing data with the default options.
     *
     * @param platform e.g. {@code rds}; see {@link #AWS_PLATFORMS}
     * @return the pricing data
     * @throws AWSPricingDataException if {@code platform} is not a platform name, or the pricing data cannot be
     *     downloaded
     * @throws IOException if the cache cannot be read or written, or the bundle is corrupt
     * @see #downloadAwsPricingData(String, AWSPricingDataOptions)
     */
    public static AWSPricingData downloadAwsPricingData(String platform) throws IOException {
        return downloadAwsPricingData(platform, AWSPricingDataOptions.builder().build());
    }

    /**
     * Downloads one AWS platform's pricing data compressed blob and decompresses it.
     *
     * <p>The bucket's {@code <platform>-latest} object ({@code latest} for EC2) names the newest bundle. With caching
     * on, a bundle is only downloaded when that names one that is not in the cache yet, and if it cannot be fetched
     * at all (offline, outage) the newest cached bundle of the same platform is used.
     *
     * @param platform e.g. {@code rds}; see {@link #AWS_PLATFORMS}. Any lowercase letters and digits are accepted.
     * @param options the options
     * @return the pricing data
     * @throws AWSPricingDataException if {@code platform} is not a platform name, or the pricing data cannot be
     *     downloaded
     * @throws IOException if the cache cannot be read or written, or the bundle is corrupt
     *     ({@link InterruptedIOException} if the thread is interrupted)
     */
    public static AWSPricingData downloadAwsPricingData(String platform, AWSPricingDataOptions options)
            throws IOException {
        if (!PLATFORM.matcher(platform).matches()) {
            throw new AWSPricingDataException("\"" + platform + "\" is not a platform name.");
        }
        // EC2's keys have no prefix because they were published before the other platforms.
        String prefix = platform.equals("ec2") ? "" : platform + "-";
        String token = options.token().orElseGet(() -> System.getenv("INFRAWRENCH_API_KEY"));
        if (token == null || token.isEmpty()) {
            throw new AWSPricingDataException("No Infrawrench API token: pass `token` or set INFRAWRENCH_API_KEY.");
        }
        String baseUrl = options.baseUrl().replaceFirst("/+$", "");
        boolean cache = options.cachePricingData();
        Path cachePath = options.cachePath();

        String name;
        try {
            String latest = jsTrim(text(baseUrl + "/" + prefix + "latest", token));
            if (!LATEST.matcher(latest).matches()) {
                throw new AWSPricingDataException(
                        prefix + "latest holds \"" + latest + "\", which is not a timestamp.");
            }
            name = prefix + "bundle-" + latest + ".json";
        } catch (InterruptedIOException e) {
            throw e;
        } catch (IOException e) {
            // A rejected token is a real answer; anything else falls back to what we already have.
            boolean rejected = e instanceof AWSPricingDataException a && a.status().orElse(0) == 401;
            Optional<String> cached = cache && !rejected ? newestCached(cachePath, prefix) : Optional.empty();
            if (cached.isEmpty()) throw e;
            name = cached.get();
        }

        // The cache holds the decompressed JSON: xz decompression is most of a load, reading the file is not.
        Path file = cachePath.resolve(name);
        if (cache) {
            InputStream in = openIfReadable(file);
            if (in != null) {
                try (in) {
                    return BundleParser.parse(in);
                }
            }
        }
        String url = baseUrl + "/" + name + ".xz";
        HttpResponse<InputStream> res = download(url, token);
        try (InputStream json = new XZInputStream(new BufferedInputStream(new Transport(res.body(), url), 1 << 16))) {
            if (!cache) return BundleParser.parse(json);
            Files.createDirectories(cachePath);
            // Write then rename, so a crash mid-write never leaves a truncated bundle to be read next time.
            Path tmp = cachePath.resolve(name + "." + ProcessHandle.current().pid() + ".tmp");
            try {
                Files.copy(json, tmp, StandardCopyOption.REPLACE_EXISTING);
            } catch (IOException | RuntimeException e) {
                Files.deleteIfExists(tmp);
                throw e;
            }
            Files.move(tmp, file, StandardCopyOption.ATOMIC_MOVE);
        }
        // This platform's older bundles, including compressed ones cached by earlier versions of this SDK.
        try (DirectoryStream<Path> dir = Files.newDirectoryStream(cachePath)) {
            for (Path f : dir) {
                String n = f.getFileName().toString();
                if (!n.equals(name) && isBundle(n, prefix, OLD_BUNDLE)) Files.deleteIfExists(f);
            }
        } catch (DirectoryIteratorException e) {
            throw e.getCause();
        }
        try (InputStream in = Files.newInputStream(file)) {
            return BundleParser.parse(in);
        }
    }

    /** GETs {@code url}, retrying the 503 the bundles Worker answers when it cannot reach the Infrawrench API. */
    private static HttpResponse<InputStream> download(String url, String token) throws IOException {
        HttpRequest request;
        try {
            request = HttpRequest.newBuilder(URI.create(url))
                    .header("Authorization", "Bearer " + token)
                    .header("User-Agent", USER_AGENT)
                    .timeout(Duration.ofMinutes(5))
                    .GET()
                    .build();
        } catch (IllegalArgumentException e) {
            throw new AWSPricingDataException("GET " + url + " failed: " + e.getMessage(), e);
        }
        for (int attempt = 1; ; attempt++) {
            HttpResponse<InputStream> res;
            try {
                res = Http.CLIENT.send(request, HttpResponse.BodyHandlers.ofInputStream());
            } catch (InterruptedException e) {
                throw interrupted(url, e);
            } catch (IOException e) {
                throw new AWSPricingDataException("GET " + url + " failed: " + e, e);
            }
            int status = res.statusCode();
            if (status >= 200 && status < 300) return res;
            res.body().close();
            if (status == 401) {
                throw new AWSPricingDataException(
                        "The Infrawrench API did not accept the token (unknown, revoked or expired).", 401);
            }
            if (status != 503 || attempt == 3) {
                throw new AWSPricingDataException("GET " + url + " failed with status " + status + ".", status);
            }
            double retryAfter = res.headers().firstValue("Retry-After").map(BulkInstances::seconds).orElse(0.0);
            try {
                Thread.sleep((long) (Math.max(0, retryAfter == 0 ? 5 : retryAfter) * 1000));
            } catch (InterruptedException e) {
                throw interrupted(url, e);
            }
        }
    }

    /** The body of {@code url}, decoded as UTF-8. */
    private static String text(String url, String token) throws IOException {
        try (InputStream in = new Transport(download(url, token).body(), url)) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    /** A numeric {@code Retry-After}, or 0 if it is not a number. */
    private static double seconds(String header) {
        String s = jsTrim(header);
        return RETRY_AFTER.matcher(s).matches() ? Double.parseDouble(s) : 0;
    }

    /** Trims the characters JavaScript's {@code String.prototype.trim} does. */
    private static String jsTrim(String s) {
        int start = 0, end = s.length();
        while (start < end && isJsSpace(s.charAt(start))) start++;
        while (end > start && isJsSpace(s.charAt(end - 1))) end--;
        return s.substring(start, end);
    }

    private static boolean isJsSpace(char c) {
        return (c >= '\t' && c <= '\r') || c == ' ' || c == ' ' || c == '﻿'
                || Character.getType(c) == Character.SPACE_SEPARATOR;
    }

    private static InterruptedIOException interrupted(String url, InterruptedException e) {
        Thread.currentThread().interrupt();
        InterruptedIOException out = new InterruptedIOException("GET " + url + " was interrupted.");
        out.initCause(e);
        return out;
    }

    /** Whether {@code name} is a bundle file of the platform with this prefix. */
    private static boolean isBundle(String name, String prefix, Pattern bundle) {
        return name.startsWith(prefix) && bundle.matcher(name.substring(prefix.length())).matches();
    }

    /** The newest bundle for a platform already in the cache directory, if any. */
    private static Optional<String> newestCached(Path cachePath, String prefix) {
        String newest = null;
        try (DirectoryStream<Path> dir = Files.newDirectoryStream(cachePath)) {
            for (Path f : dir) {
                String n = f.getFileName().toString();
                if (isBundle(n, prefix, BUNDLE) && (newest == null || n.compareTo(newest) > 0)) newest = n;
            }
        } catch (IOException | DirectoryIteratorException e) {
            return Optional.empty();
        }
        return Optional.ofNullable(newest);
    }

    private static InputStream openIfReadable(Path file) {
        if (Files.isDirectory(file)) return null;
        try {
            return Files.newInputStream(file);
        } catch (IOException e) {
            return null;
        }
    }

    /** A response body whose read failures are {@link AWSPricingDataException}s, like the request's own. */
    private static final class Transport extends FilterInputStream {
        private final String url;

        Transport(InputStream in, String url) {
            super(in);
            this.url = url;
        }

        @Override
        public int read() throws IOException {
            try {
                return super.read();
            } catch (IOException e) {
                throw wrap(e);
            }
        }

        @Override
        public int read(byte[] b, int off, int len) throws IOException {
            try {
                return super.read(b, off, len);
            } catch (IOException e) {
                throw wrap(e);
            }
        }

        private IOException wrap(IOException e) {
            if (e instanceof InterruptedIOException) return e;
            return new AWSPricingDataException("GET " + url + " failed: " + e, e);
        }
    }
}
