#![doc = include_str!("../README.md")]

mod data;
mod error;
mod raw;

use std::io::{ErrorKind, Read};
use std::path::{Path, PathBuf};
use std::time::Duration;
use std::{env, fmt, fs, process, thread};

use ureq::http::Response;
use ureq::{Agent, Body};

pub use crate::data::{
    AttributeChange, AwsInstance, AwsPricingData, OnDemandPrice, OnDemandPriceChange, Pricing,
    PricingHistory, Regions, ReservedPrice, ReservedPriceChange, ReservedTerm, Variant,
};
pub use crate::error::Error;

const DEFAULT_BASE_URL: &str = "https://instances-bundles.infrawrench.com";
const USER_AGENT: &str = "infrawrench/bulk-instances, rust, 1.0";

/// Options for [`download_aws_ec2_pricing_data`].
///
/// ```
/// let options = infrawrench_bulk_instances::Options {
///     cache_pricing_data: false,
///     ..Default::default()
/// };
/// ```
#[derive(Clone)]
pub struct Options {
    /// Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable.
    pub token: Option<String>,

    /// Whether to cache the pricing data. Defaults to true.
    pub cache_pricing_data: bool,

    /// The cache path. Defaults to ~/.infrawrench/aws_pricing_data
    pub cache_path: Option<PathBuf>,

    /// Where the bundles are served from. Defaults to <https://instances-bundles.infrawrench.com>
    pub base_url: Option<String>,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            token: None,
            cache_pricing_data: true,
            cache_path: None,
            base_url: None,
        }
    }
}

impl fmt::Debug for Options {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Options")
            .field("token", &self.token.as_ref().map(|_| "<redacted>"))
            .field("cache_pricing_data", &self.cache_pricing_data)
            .field("cache_path", &self.cache_path)
            .field("base_url", &self.base_url)
            .finish()
    }
}

fn get(agent: &Agent, url: &str, token: &str) -> Result<Response<Body>, Error> {
    agent
        .get(url)
        .header("Authorization", format!("Bearer {token}"))
        .call()
        .map_err(|e| Error::with_source(format!("GET {url} failed."), e))
}

/// GETs `url`, retrying the 503 the bundles Worker answers when it cannot reach the Infrawrench API.
fn download(agent: &Agent, url: &str, token: &str) -> Result<Response<Body>, Error> {
    let mut attempt = 1;
    loop {
        let res = get(agent, url, token)?;
        let status = res.status().as_u16();
        if res.status().is_success() {
            return Ok(res);
        }
        if status == 401 {
            return Err(Error::with_status(
                "The Infrawrench API did not accept the token (unknown, revoked or expired).",
                401,
            ));
        }
        if status != 503 || attempt == 3 {
            return Err(Error::with_status(
                format!("GET {url} failed with status {status}."),
                status,
            ));
        }
        let retry_after = res
            .headers()
            .get("retry-after")
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.trim().parse::<f64>().ok())
            .filter(|&s| s.is_finite() && s != 0.0)
            .unwrap_or(5.0);
        drop(res);
        thread::sleep(Duration::from_secs_f64(retry_after.max(0.0)));
        attempt += 1;
    }
}

/// Whether `f` is a cached bundle (`bundle-<latest>.json`, or with `.xz` if `xz`).
fn is_bundle(f: &str, xz: bool) -> bool {
    let Some(rest) = f.strip_prefix("bundle-") else {
        return false;
    };
    let stem = rest
        .strip_suffix(".json")
        .or_else(|| rest.strip_suffix(".json.xz").filter(|_| xz));
    stem.is_some_and(|s| !s.is_empty() && !s.contains(['\n', '\r', '\u{2028}', '\u{2029}']))
}

/// The newest bundle already in the cache directory, if any.
fn newest_cached(cache_path: &Path) -> Option<String> {
    let mut files: Vec<String> = fs::read_dir(cache_path)
        .ok()?
        .filter_map(|e| e.ok()?.file_name().into_string().ok())
        .filter(|f| is_bundle(f, false))
        .collect();
    files.sort();
    files.pop()
}

/// The bundle name `latest` points at, e.g. `bundle-20261001T000000Z.json`.
fn latest_name(agent: &Agent, base_url: &str, token: &str) -> Result<String, Error> {
    let url = format!("{base_url}/latest");
    let mut body = Vec::new();
    download(agent, &url, token)?
        .body_mut()
        .as_reader()
        .read_to_end(&mut body)
        .map_err(|e| Error::with_source(format!("GET {url} failed."), e))?;
    let body = String::from_utf8_lossy(&body);
    // What JavaScript's `trim` strips.
    let latest =
        body.trim_matches(|c: char| (c.is_whitespace() && c != '\u{85}') || c == '\u{feff}');
    if latest.is_empty()
        || !latest
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b))
    {
        return Err(Error::new(format!(
            "latest holds \"{latest}\", which is not a timestamp."
        )));
    }
    Ok(format!("bundle-{latest}.json"))
}

/// Downloads the AWS EC2 pricing data compressed blob and decompresses it.
///
/// The bucket's `latest` object names the newest bundle. With caching on, a bundle
/// is only downloaded when `latest` names one that is not in the cache yet, and if
/// `latest` cannot be fetched at all (offline, outage) the newest cached bundle is used.
///
/// This blocks on network and disk I/O. From async code, run it on a blocking thread, e.g.
/// with `tokio::task::spawn_blocking`.
pub fn download_aws_ec2_pricing_data(options: &Options) -> Result<AwsPricingData, Error> {
    let token = options
        .token
        .clone()
        .or_else(|| env::var("INFRAWRENCH_API_KEY").ok())
        .filter(|t| !t.is_empty())
        .ok_or_else(|| {
            Error::new("No Infrawrench API token: pass `token` or set INFRAWRENCH_API_KEY.")
        })?;
    let base_url = options
        .base_url
        .as_deref()
        .unwrap_or(DEFAULT_BASE_URL)
        .trim_end_matches('/');
    let cache_path = match (options.cache_pricing_data, &options.cache_path) {
        (false, _) => None,
        (true, Some(path)) => Some(path.clone()),
        (true, None) => Some(
            env::home_dir()
                .ok_or_else(|| {
                    Error::new(
                        "No home directory: pass `cache_path` or turn `cache_pricing_data` off.",
                    )
                })?
                .join(".infrawrench")
                .join("aws_pricing_data"),
        ),
    };
    let agent: Agent = Agent::config_builder()
        .http_status_as_error(false)
        .user_agent(USER_AGENT)
        .build()
        .into();

    let name = match latest_name(&agent, base_url, &token) {
        Ok(name) => name,
        // A rejected token is a real answer; anything else falls back to what we already have.
        Err(err) => match &cache_path {
            Some(path) if err.status() != Some(401) => newest_cached(path).ok_or(err)?,
            _ => return Err(err),
        },
    };

    // The cache holds the decompressed JSON: xz decompression is most of a load, reading the file is not.
    let cached = cache_path
        .as_ref()
        .and_then(|path| fs::read(path.join(&name)).ok());
    let json = match cached {
        Some(json) => json,
        None => {
            let url = format!("{base_url}/{name}.xz");
            let mut res = download(&agent, &url, &token)?;
            let mut json = Vec::new();
            liblzma::read::XzDecoder::new(res.body_mut().as_reader())
                .read_to_end(&mut json)
                .map_err(|e| {
                    Error::with_source(format!("GET {url} could not be decompressed."), e)
                })?;
            if let Some(path) = &cache_path {
                write_cache(path, &name, &json).map_err(|e| {
                    Error::with_source(format!("Could not cache {name} in {}.", path.display()), e)
                })?;
            }
            json
        }
    };

    let raw = serde_json::from_slice(&json)
        .map_err(|e| Error::with_source(format!("{name} is not a valid bundle."), e))?;
    Ok(AwsPricingData::new(raw))
}

fn write_cache(cache_path: &Path, name: &str, json: &[u8]) -> std::io::Result<()> {
    fs::create_dir_all(cache_path)?;
    // Write then rename, so a crash mid-write never leaves a truncated bundle to be read next time.
    let tmp = cache_path.join(format!("{name}.{}.tmp", process::id()));
    fs::write(&tmp, json)?;
    fs::rename(&tmp, cache_path.join(name))?;
    // Older bundles, including compressed ones cached by earlier versions of this SDK.
    for entry in fs::read_dir(cache_path)? {
        let entry = entry?;
        if entry
            .file_name()
            .to_str()
            .is_some_and(|f| f != name && is_bundle(f, true))
        {
            match fs::remove_file(entry.path()) {
                Err(e) if e.kind() != ErrorKind::NotFound => return Err(e),
                _ => {}
            }
        }
    }
    Ok(())
}
