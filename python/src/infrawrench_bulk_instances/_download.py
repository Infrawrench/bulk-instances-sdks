from __future__ import annotations

import json
import lzma
import math
import os
import re
import time
import urllib.error
import urllib.request
from http.client import HTTPException
from pathlib import Path

from ._data import AWSPricingData

DEFAULT_BASE_URL = "https://instances-bundles.infrawrench.com"
_USER_AGENT = "infrawrench/bulk-instances, python, 1.0"


class AWSPricingDataError(Exception):
    """Raised when the pricing data cannot be downloaded. ``status`` is the HTTP status, if there was a response."""

    status: int | None

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _retry_after(value: str | None) -> float:
    try:
        seconds = float(value) if value else 0.0
    except ValueError:
        seconds = 0.0
    return seconds if math.isfinite(seconds) and seconds != 0 else 5.0


def _download(url: str, token: str) -> bytes:
    """GETs ``url``, retrying the 503 the bundles Worker answers when it cannot reach the Infrawrench API."""
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": _USER_AGENT})
    attempt = 1
    while True:
        try:
            with urllib.request.urlopen(request) as res:
                body: bytes = res.read()
                return body
        except urllib.error.HTTPError as err:
            status, retry_after = err.code, err.headers.get("Retry-After")
            err.close()
        except (urllib.error.URLError, HTTPException, OSError) as err:
            reason = err.reason if isinstance(err, urllib.error.URLError) else err
            raise AWSPricingDataError(f"GET {url} failed: {reason}") from err
        if status == 401:
            raise AWSPricingDataError(
                "The Infrawrench API did not accept the token (unknown, revoked or expired).", 401
            )
        if status != 503 or attempt == 3:
            raise AWSPricingDataError(f"GET {url} failed with status {status}.", status)
        time.sleep(max(_retry_after(retry_after), 0.0))
        attempt += 1


_CACHED_BUNDLE = re.compile(r"bundle-.+\.json")
_OLD_BUNDLE = re.compile(r"bundle-.+\.json(\.xz)?")


def _newest_cached(cache_path: Path) -> str | None:
    """The newest bundle already in the cache directory, if any."""
    try:
        files = os.listdir(cache_path)
    except OSError:
        return None
    bundles = sorted(f for f in files if _CACHED_BUNDLE.fullmatch(f))
    return bundles[-1] if bundles else None


def download_aws_ec2_pricing_data(
    *,
    token: str | None = None,
    cache_pricing_data: bool = True,
    cache_path: str | os.PathLike[str] | None = None,
    base_url: str | None = None,
) -> AWSPricingData:
    """Downloads the AWS EC2 pricing data compressed blob and decompresses it.

    The bucket's ``latest`` object names the newest bundle. With caching on, a bundle
    is only downloaded when ``latest`` names one that is not in the cache yet, and if
    ``latest`` cannot be fetched at all (offline, outage) the newest cached bundle is used.

    :param token: Defines your Infrawrench API token. Defaults to the ``INFRAWRENCH_API_KEY`` environment variable.
    :param cache_pricing_data: Whether to cache the pricing data. Defaults to true.
    :param cache_path: The cache path. Defaults to ``~/.infrawrench/aws_pricing_data``.
    :param base_url: Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
    :raises AWSPricingDataError: When the token is missing or rejected, or the bundle cannot be fetched.
    """
    if token is None:
        token = os.environ.get("INFRAWRENCH_API_KEY")
    if not token:
        raise AWSPricingDataError("No Infrawrench API token: pass `token` or set INFRAWRENCH_API_KEY.")
    base_url = (DEFAULT_BASE_URL if base_url is None else base_url).rstrip("/")
    cache = cache_pricing_data
    cache_dir = Path.home() / ".infrawrench" / "aws_pricing_data" if cache_path is None else Path(cache_path)

    try:
        latest = _download(f"{base_url}/latest", token).decode("utf-8", errors="replace").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]+", latest):
            raise AWSPricingDataError(f'latest holds "{latest}", which is not a timestamp.')
        name = f"bundle-{latest}.json"
    except Exception as err:
        # A rejected token is a real answer; anything else falls back to what we already have.
        cached = (
            _newest_cached(cache_dir)
            if cache and not (isinstance(err, AWSPricingDataError) and err.status == 401)
            else None
        )
        if cached is None:
            raise
        name = cached

    # The cache holds the decompressed JSON: xz decompression is most of a load, reading the file is not.
    text: str | None = None
    if cache:
        try:
            with open(cache_dir / name, encoding="utf-8", errors="replace", newline="") as file:
                text = file.read()
        except OSError:
            pass
    if text is None:
        compressed = _download(f"{base_url}/{name}.xz", token)
        text = lzma.decompress(compressed, format=lzma.FORMAT_XZ).decode("utf-8-sig", errors="replace")
        del compressed
        if cache:
            cache_dir.mkdir(parents=True, exist_ok=True)
            # Write then rename, so a crash mid-write never leaves a truncated bundle to be read next time.
            tmp = cache_dir / f"{name}.{os.getpid()}.tmp"
            tmp.write_text(text, encoding="utf-8", newline="")
            os.replace(tmp, cache_dir / name)
            # Older bundles, including compressed ones cached by earlier versions of this SDK.
            for f in os.listdir(cache_dir):
                if f != name and _OLD_BUNDLE.fullmatch(f):
                    (cache_dir / f).unlink(missing_ok=True)

    return AWSPricingData(json.loads(text))
