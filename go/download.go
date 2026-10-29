package bulkinstances

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"math"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/ulikunitz/xz"
)

// Options configures [DownloadAWSEC2PricingData]. The zero value uses every default.
type Options struct {
	// Token is your Infrawrench API token. Defaults to the INFRAWRENCH_API_KEY environment variable.
	Token string

	// DisableCache turns off caching of the pricing data, which is on by default.
	DisableCache bool

	// CachePath is the cache directory. Defaults to ~/.infrawrench/aws_pricing_data.
	CachePath string

	// BaseURL is where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com.
	BaseURL string

	// HTTPClient makes the requests. Defaults to http.DefaultClient.
	HTTPClient *http.Client
}

const (
	defaultBaseURL = "https://instances-bundles.infrawrench.com"
	userAgent      = "infrawrench/bulk-instances, go, 1.0"
)

var (
	latestName     = regexp.MustCompile(`^[A-Za-z0-9._-]+$`)
	cachedBundle   = regexp.MustCompile(`^bundle-.+\.json$`)
	obsoleteBundle = regexp.MustCompile(`^bundle-.+\.json(\.xz)?$`)
)

// Error is returned when the pricing data cannot be downloaded. Use [errors.As] to
// detect it.
type Error struct {
	// Status is the HTTP status, if there was a response, or 0.
	Status int
	// Message describes the failure.
	Message string
	// Err is the transport error that caused the failure, if any.
	Err error
}

func (e *Error) Error() string {
	if e.Err == nil {
		return e.Message
	}
	return e.Message + ": " + e.Err.Error()
}

// Unwrap returns the transport error that caused the failure, if any.
func (e *Error) Unwrap() error { return e.Err }

func transportError(rawURL string, err error) *Error {
	// The url.Error repeats the URL that the message already names.
	var ue *url.Error
	if errors.As(err, &ue) {
		err = ue.Err
	}
	return &Error{Message: "GET " + rawURL + " failed", Err: err}
}

func get(ctx context.Context, client *http.Client, rawURL, token string) (*http.Response, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, rawURL, nil)
	if err != nil {
		return nil, transportError(rawURL, err)
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", userAgent)
	res, err := client.Do(req)
	if err != nil {
		return nil, transportError(rawURL, err)
	}
	return res, nil
}

// download GETs rawURL, retrying the 503 the bundles Worker answers when it cannot
// reach the Infrawrench API.
func download(ctx context.Context, client *http.Client, rawURL, token string) (*http.Response, error) {
	for attempt := 1; ; attempt++ {
		res, err := get(ctx, client, rawURL, token)
		if err != nil {
			return nil, err
		}
		if res.StatusCode >= 200 && res.StatusCode <= 299 {
			return res, nil
		}
		_, _ = io.Copy(io.Discard, io.LimitReader(res.Body, 64<<10))
		res.Body.Close()
		if res.StatusCode == http.StatusUnauthorized {
			return nil, &Error{Status: res.StatusCode, Message: "The Infrawrench API did not accept the token (unknown, revoked or expired)."}
		}
		if res.StatusCode != http.StatusServiceUnavailable || attempt == 3 {
			return nil, &Error{Status: res.StatusCode, Message: fmt.Sprintf("GET %s failed with status %d.", rawURL, res.StatusCode)}
		}
		timer := time.NewTimer(retryAfter(res.Header.Get("Retry-After")))
		select {
		case <-ctx.Done():
			timer.Stop()
			return nil, transportError(rawURL, ctx.Err())
		case <-timer.C:
		}
	}
}

// retryAfter reads a Retry-After header in seconds. Missing, zero or unparseable means 5.
func retryAfter(header string) time.Duration {
	secs, err := strconv.ParseFloat(strings.TrimSpace(header), 64)
	if err != nil || secs == 0 || math.IsNaN(secs) || math.IsInf(secs, 0) {
		secs = 5
	}
	return time.Duration(secs * float64(time.Second))
}

// newestCached returns the newest bundle already in the cache directory, or "" if there is none.
func newestCached(cachePath string) string {
	entries, err := os.ReadDir(cachePath)
	if err != nil {
		return ""
	}
	newest := ""
	for _, e := range entries {
		if cachedBundle.MatchString(e.Name()) && e.Name() > newest {
			newest = e.Name()
		}
	}
	return newest
}

// DownloadAWSEC2PricingData downloads the AWS EC2 pricing data compressed blob and
// decompresses it.
//
// The bucket's latest object names the newest bundle. With caching on, a bundle
// is only downloaded when latest names one that is not in the cache yet, and if
// latest cannot be fetched at all (offline, outage) the newest cached bundle is used.
//
// Download failures are returned as an [*Error]; cache, decompression and parsing
// failures are returned as they are.
func DownloadAWSEC2PricingData(ctx context.Context, opts Options) (*AWSPricingData, error) {
	token := opts.Token
	if token == "" {
		token = os.Getenv("INFRAWRENCH_API_KEY")
	}
	if token == "" {
		return nil, &Error{Message: "No Infrawrench API token: pass Options.Token or set INFRAWRENCH_API_KEY."}
	}
	baseURL := opts.BaseURL
	if baseURL == "" {
		baseURL = defaultBaseURL
	}
	baseURL = strings.TrimRight(baseURL, "/")
	cache := !opts.DisableCache
	cachePath := opts.CachePath
	if cache && cachePath == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return nil, fmt.Errorf("bulkinstances: finding the default cache path: %w", err)
		}
		cachePath = filepath.Join(home, ".infrawrench", "aws_pricing_data")
	}
	client := opts.HTTPClient
	if client == nil {
		client = http.DefaultClient
	}

	name, err := latestBundle(ctx, client, baseURL, token)
	if err != nil {
		// A rejected token is a real answer, and so is a cancelled context; anything
		// else falls back to what we already have.
		var e *Error
		cached := ""
		if cache && !(errors.As(err, &e) && e.Status == http.StatusUnauthorized) && ctx.Err() == nil {
			cached = newestCached(cachePath)
		}
		if cached == "" {
			return nil, err
		}
		name = cached
	}

	// The cache holds the decompressed JSON: xz decompression is most of a load, reading the file is not.
	var json []byte
	found := false
	if cache {
		json, err = os.ReadFile(filepath.Join(cachePath, name))
		found = err == nil
	}
	if !found {
		json, err = downloadBundle(ctx, client, baseURL+"/"+name+".xz", token)
		if err != nil {
			return nil, err
		}
		if cache {
			if err := store(cachePath, name, json); err != nil {
				return nil, err
			}
		}
	}

	return parseBundle(json)
}

// latestBundle returns the file name of the bundle the bucket's latest object names.
func latestBundle(ctx context.Context, client *http.Client, baseURL, token string) (string, error) {
	rawURL := baseURL + "/latest"
	res, err := download(ctx, client, rawURL, token)
	if err != nil {
		return "", err
	}
	defer res.Body.Close()
	body, err := io.ReadAll(res.Body)
	if err != nil {
		return "", transportError(rawURL, err)
	}
	latest := strings.TrimSpace(string(body))
	if !latestName.MatchString(latest) {
		return "", &Error{Message: fmt.Sprintf("latest holds %q, which is not a timestamp.", latest)}
	}
	return "bundle-" + latest + ".json", nil
}

// downloadBundle GETs the xz-compressed bundle at rawURL and returns it decompressed.
func downloadBundle(ctx context.Context, client *http.Client, rawURL, token string) ([]byte, error) {
	res, err := download(ctx, client, rawURL, token)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	body := &bodyReader{r: res.Body}
	r, err := xz.NewReader(bufio.NewReaderSize(body, 1<<16))
	var json []byte
	if err == nil {
		json, err = io.ReadAll(r)
	}
	if err != nil {
		if body.err != nil {
			return nil, transportError(rawURL, body.err)
		}
		return nil, fmt.Errorf("bulkinstances: decompressing %s: %w", rawURL, err)
	}
	return json, nil
}

// bodyReader remembers a failure to read the response body, so it can be told
// apart from a decompression failure.
type bodyReader struct {
	r   io.Reader
	err error
}

func (b *bodyReader) Read(p []byte) (int, error) {
	n, err := b.r.Read(p)
	if err != nil && err != io.EOF {
		b.err = err
	}
	return n, err
}

// store writes the decompressed bundle to the cache and deletes every older one.
func store(cachePath, name string, json []byte) error {
	if err := os.MkdirAll(cachePath, 0o777); err != nil {
		return err
	}
	// Write then rename, so a crash mid-write never leaves a truncated bundle to be read next time.
	tmp := filepath.Join(cachePath, fmt.Sprintf("%s.%d.tmp", name, os.Getpid()))
	if err := os.WriteFile(tmp, json, 0o666); err != nil {
		return err
	}
	if err := os.Rename(tmp, filepath.Join(cachePath, name)); err != nil {
		return err
	}
	// Older bundles, including compressed ones cached by earlier versions of this SDK.
	entries, err := os.ReadDir(cachePath)
	if err != nil {
		return err
	}
	for _, e := range entries {
		if e.Name() != name && obsoleteBundle.MatchString(e.Name()) {
			if err := os.Remove(filepath.Join(cachePath, e.Name())); err != nil && !errors.Is(err, fs.ErrNotExist) {
				return err
			}
		}
	}
	return nil
}
