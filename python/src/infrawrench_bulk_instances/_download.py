from __future__ import annotations

import json
import lzma
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.client import HTTPException
from pathlib import Path
from typing import Any, Final, cast

from ._data import (
    AlibabaInstance,
    AlibabaPricingData,
    AWSInstance,
    AWSPricingData,
    AzurePricingData,
    GCPPricingData,
    RunpodInstance,
    RunpodPricingData,
)

DEFAULT_BASE_URL = "https://instances-bundles.infrawrench.com"
DEFAULT_API_URL = "https://app.infrawrench.com"
_USER_AGENT = "infrawrench/bulk-instances, python, 1.0"


class AWSPricingDataError(Exception):
    """Raised when the pricing data cannot be downloaded. ``status`` is the HTTP status, if there was a response."""

    status: int | None

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class RunpodPricingDataError(AWSPricingDataError):
    """Raised when RunPod's pricing data cannot be downloaded. ``status`` is the HTTP status, if there was a response."""


class AlibabaPricingDataError(AWSPricingDataError):
    """Raised when Alibaba Cloud's pricing data cannot be downloaded. ``status`` is the HTTP status, if there was
    a response."""


class AzurePricingDataError(AWSPricingDataError):
    """Raised when Azure's pricing data cannot be downloaded. ``status`` is the HTTP status, if there was a response."""


class GCPPricingDataError(AWSPricingDataError):
    """Raised when Google Cloud's pricing data cannot be downloaded. ``status`` is the HTTP status, if there was a
    response."""


def _retry_after(value: str | None) -> float:
    try:
        seconds = float(value) if value else 0.0
    except ValueError:
        seconds = 0.0
    return seconds if math.isfinite(seconds) and seconds != 0 else 5.0


def _download(url: str, token: str) -> bytes:
    """GETs ``url``, retrying the 503 the bundles Worker answers when it cannot reach the Infrawrench API
    (and the API answers when it cannot reach its store)."""
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


def _is_bundle(f: str, prefix: str, pattern: re.Pattern[str]) -> bool:
    """Whether ``f`` is one of this platform's bundles. EC2's (no prefix) never matches another platform's."""
    return f.startswith(prefix) and pattern.fullmatch(f[len(prefix):]) is not None


def _newest_cached(cache_path: Path, prefix: str) -> str | None:
    """The newest bundle for a platform already in the cache directory, if any."""
    try:
        files = os.listdir(cache_path)
    except OSError:
        return None
    bundles = sorted(f for f in files if _is_bundle(f, prefix, _CACHED_BUNDLE))
    return bundles[-1] if bundles else None


AWS_PLATFORMS: Final[tuple[str, ...]] = (
    "ec2", "rds", "elasticache", "opensearch", "redshift", "docdb", "neptune", "memorydb", "dax", "sagemaker", "emr",
    "gamelift", "spot",
)
"""The AWS platforms Infrawrench publishes a bundle for. Any other lowercase name is
requested as is, so a platform added later works without a new SDK."""

def download_aws_ec2_pricing_data(
    *,
    token: str | None = None,
    cache_pricing_data: bool = True,
    cache_path: str | os.PathLike[str] | None = None,
    base_url: str | None = None,
) -> AWSPricingData:
    """Downloads the AWS EC2 pricing data. The same as ``download_aws_pricing_data("ec2", ...)``."""
    return download_aws_pricing_data(
        "ec2", token=token, cache_pricing_data=cache_pricing_data, cache_path=cache_path, base_url=base_url
    )


def download_aws_pricing_data(
    platform: str,
    *,
    token: str | None = None,
    cache_pricing_data: bool = True,
    cache_path: str | os.PathLike[str] | None = None,
    base_url: str | None = None,
) -> AWSPricingData:
    """Downloads one AWS platform's pricing data compressed blob and decompresses it.

    The bucket's ``<platform>-latest`` object (``latest`` for EC2) names the newest bundle. With
    caching on, a bundle is only downloaded when that names one that is not in the cache yet,
    and if it cannot be fetched at all (offline, outage) the newest cached bundle is used.

    :param platform: The platform, e.g. ``"ec2"`` or ``"rds"`` (see :data:`AWS_PLATFORMS`).
    :param token: Defines your Infrawrench API token. Defaults to the ``INFRAWRENCH_API_KEY`` environment variable.
    :param cache_pricing_data: Whether to cache the pricing data. Defaults to true.
    :param cache_path: The cache path. Defaults to ``~/.infrawrench/aws_pricing_data``.
    :param base_url: Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
    :raises AWSPricingDataError: When the platform name is malformed, the token is missing or rejected,
        or the bundle cannot be fetched.
    """
    return AWSPricingData(
        _load_bundle(platform, token=token, cache_pricing_data=cache_pricing_data, cache_path=cache_path, base_url=base_url)
    )


def download_runpod_pricing_data(
    *,
    token: str | None = None,
    cache_pricing_data: bool = True,
    cache_path: str | os.PathLike[str] | None = None,
    base_url: str | None = None,
) -> RunpodPricingData:
    """Downloads RunPod's pricing data: GPU types (priced per GPU per hour) and CPU pods (per pod per hour).

    Caching and the offline fallback work as for :func:`download_aws_pricing_data`, and it takes the same
    keyword arguments.

    :raises RunpodPricingDataError: When the token is missing or rejected, or the bundle cannot be fetched.
    """
    return RunpodPricingData(_load_bundle_as(
        "runpod", RunpodPricingDataError,
        token=token, cache_pricing_data=cache_pricing_data, cache_path=cache_path, base_url=base_url,
    ))


def download_alibaba_pricing_data(
    *,
    token: str | None = None,
    cache_pricing_data: bool = True,
    cache_path: str | os.PathLike[str] | None = None,
    base_url: str | None = None,
) -> AlibabaPricingData:
    """Downloads Alibaba Cloud's ECS pricing data: pay-as-you-go, subscription and reserved instance prices per
    region.

    Caching and the offline fallback work as for :func:`download_aws_pricing_data`, and it takes the same
    keyword arguments.

    :raises AlibabaPricingDataError: When the token is missing or rejected, or the bundle cannot be fetched.
    """
    return AlibabaPricingData(_load_bundle_as(
        "alibaba", AlibabaPricingDataError,
        token=token, cache_pricing_data=cache_pricing_data, cache_path=cache_path, base_url=base_url,
    ))


def download_azure_pricing_data(
    *,
    token: str | None = None,
    cache_pricing_data: bool = True,
    cache_path: str | os.PathLike[str] | None = None,
    base_url: str | None = None,
) -> AzurePricingData:
    """Downloads Azure's virtual machine pricing data: pay-as-you-go, Spot and Low Priority prices, reservations
    and savings plans per region.

    Caching and the offline fallback work as for :func:`download_aws_pricing_data`, and it takes the same
    keyword arguments.

    :raises AzurePricingDataError: When the token is missing or rejected, or the bundle cannot be fetched.
    """
    return AzurePricingData(_load_bundle_as(
        "azure", AzurePricingDataError,
        token=token, cache_pricing_data=cache_pricing_data, cache_path=cache_path, base_url=base_url,
    ))


def download_gcp_pricing_data(
    *,
    token: str | None = None,
    cache_pricing_data: bool = True,
    cache_path: str | os.PathLike[str] | None = None,
    base_url: str | None = None,
) -> GCPPricingData:
    """Downloads Google Cloud's Compute Engine pricing data: Standard and Spot prices and committed use discounts
    per region, for each machine type.

    Caching and the offline fallback work as for :func:`download_aws_pricing_data`, and it takes the same
    keyword arguments.

    :raises GCPPricingDataError: When the token is missing or rejected, or the bundle cannot be fetched.
    """
    return GCPPricingData(_load_bundle_as(
        "gcp", GCPPricingDataError,
        token=token, cache_pricing_data=cache_pricing_data, cache_path=cache_path, base_url=base_url,
    ))


def _load_bundle_as(
    platform: str,
    error: type[AWSPricingDataError],
    *,
    token: str | None,
    cache_pricing_data: bool,
    cache_path: str | os.PathLike[str] | None,
    base_url: str | None,
) -> Any:
    """:func:`_load_bundle`, failing with the provider's own error class."""
    with _provider_error(error):
        return _load_bundle(
            platform, token=token, cache_pricing_data=cache_pricing_data, cache_path=cache_path, base_url=base_url
        )


@contextmanager
def _provider_error(error: type[AWSPricingDataError]) -> Iterator[None]:
    """Turns an :class:`AWSPricingDataError` raised inside it into the provider's own error class."""
    try:
        yield
    except AWSPricingDataError as err:
        # Chained to what the AWS error was chained to (or nothing), so the traceback reads as if raised here.
        raise error(str(err), err.status) from err.__cause__


def _load_bundle(
    platform: str,
    *,
    token: str | None,
    cache_pricing_data: bool,
    cache_path: str | os.PathLike[str] | None,
    base_url: str | None,
) -> Any:
    """Downloads (or reads from the cache) one platform's bundle, parsed."""
    if not re.fullmatch(r"[a-z0-9]+", platform):
        raise AWSPricingDataError(f'"{platform}" is not a platform name.')
    # EC2's keys have no prefix because they were published before the other platforms.
    prefix = "" if platform == "ec2" else f"{platform}-"
    if token is None:
        token = os.environ.get("INFRAWRENCH_API_KEY")
    if not token:
        raise AWSPricingDataError("No Infrawrench API token: pass `token` or set INFRAWRENCH_API_KEY.")
    base_url = (DEFAULT_BASE_URL if base_url is None else base_url).rstrip("/")
    cache = cache_pricing_data
    cache_dir = Path.home() / ".infrawrench" / "aws_pricing_data" if cache_path is None else Path(cache_path)

    try:
        latest = _download(f"{base_url}/{prefix}latest", token).decode("utf-8", errors="replace").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]+", latest):
            raise AWSPricingDataError(f'{prefix}latest holds "{latest}", which is not a timestamp.')
        name = f"{prefix}bundle-{latest}.json"
    except Exception as err:
        # A rejected token is a real answer; anything else falls back to what we already have.
        cached = (
            _newest_cached(cache_dir, prefix)
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
            # This platform's older bundles, including compressed ones cached by earlier versions of this SDK.
            for f in os.listdir(cache_dir):
                if f != name and _is_bundle(f, prefix, _OLD_BUNDLE):
                    (cache_dir / f).unlink(missing_ok=True)

    return json.loads(text)


def fetch_aws_instance(
    platform: str,
    instance_type: str,
    *,
    token: str | None = None,
    base_url: str | None = None,
) -> AWSInstance | None:
    """Fetches one instance from the Infrawrench API, without downloading the platform's bundle.

    Nothing is cached. The result is the same as ``download_aws_pricing_data(platform).get(instance_type)``,
    from whichever bundle the API last synced, which can trail the newest bundle by up to half an hour.

    :param platform: The platform, e.g. ``"ec2"`` or ``"rds"`` (see :data:`AWS_PLATFORMS`).
    :param instance_type: The instance type, e.g. ``"m5.large"``.
    :param token: Defines your Infrawrench API token. Defaults to the ``INFRAWRENCH_API_KEY`` environment variable.
    :param base_url: Where the Infrawrench API is served from. Defaults to https://app.infrawrench.com
    :returns: The instance, or ``None`` if the platform has no instance with that name.
    :raises AWSPricingDataError: When the platform name is malformed, the instance type is empty, the token
        is missing or rejected, or the instance cannot be fetched.
    """
    return _fetch_instance(platform, instance_type, AWSPricingData, token=token, base_url=base_url)


def fetch_runpod_instance(id: str, *, token: str | None = None, base_url: str | None = None) -> RunpodInstance | None:
    """Fetches one RunPod GPU type or CPU pod from the Infrawrench API, without downloading RunPod's bundle.

    Nothing is cached. The result is the same as ``download_runpod_pricing_data().get(id)``, from whichever
    bundle the API last synced, which can trail the newest bundle by up to half an hour. It takes the same keyword
    arguments as :func:`fetch_aws_instance`.

    :param id: The GPU type id (``"NVIDIA H100 80GB HBM3"``) or CPU pod id (``"cpu3c-2-4"``).
    :returns: The instance, or ``None`` if RunPod has no instance with that id.
    :raises RunpodPricingDataError: When the id is empty, the token is missing or rejected, or the instance
        cannot be fetched.
    """
    with _provider_error(RunpodPricingDataError):
        one = _fetch_instance("runpod", id, RunpodPricingData, token=token, base_url=base_url)
    return cast("RunpodInstance | None", one)


def fetch_alibaba_instance(
    instance_type: str, *, token: str | None = None, base_url: str | None = None
) -> AlibabaInstance | None:
    """Fetches one Alibaba Cloud ECS instance type from the Infrawrench API, without downloading Alibaba's bundle.

    Nothing is cached. The result is the same as ``download_alibaba_pricing_data().get(instance_type)``, from
    whichever bundle the API last synced, which can trail the newest bundle by up to half an hour. It takes the
    same keyword arguments as :func:`fetch_aws_instance`.

    :param instance_type: The instance type, e.g. ``"ecs.g6.large"``.
    :returns: The instance, or ``None`` if Alibaba has no instance type with that name.
    :raises AlibabaPricingDataError: When the instance type is empty, the token is missing or rejected, or the
        instance cannot be fetched.
    """
    with _provider_error(AlibabaPricingDataError):
        one = _fetch_instance("alibaba", instance_type, AlibabaPricingData, token=token, base_url=base_url)
    return cast("AlibabaInstance | None", one)


def _fetch_instance(
    platform: str,
    instance_type: str,
    data_class: Callable[[Any], AWSPricingData],
    *,
    token: str | None,
    base_url: str | None,
) -> AWSInstance | None:
    """GETs one instance from the Infrawrench API and decodes it with ``data_class``, whose ``get`` gives
    the instance type."""
    if not re.fullmatch(r"[a-z0-9]+", platform):
        raise AWSPricingDataError(f'"{platform}" is not a platform name.')
    if instance_type == "":
        raise AWSPricingDataError("The instance type is empty.")
    if token is None:
        token = os.environ.get("INFRAWRENCH_API_KEY")
    if not token:
        raise AWSPricingDataError("No Infrawrench API token: pass `token` or set INFRAWRENCH_API_KEY.")
    base_url = (DEFAULT_API_URL if base_url is None else base_url).rstrip("/")
    try:
        name = urllib.parse.quote(instance_type, safe="")
        body = _download(f"{base_url}/api/v1/aws-bulk-pricing/{platform}/{name}", token)
    except AWSPricingDataError as err:
        if err.status == 404:
            return None
        raise
    # The bundle's tables cut down to what this instance uses, and its row renumbered to match.
    value = json.loads(body)
    name = value["name"]
    return data_class({**value, "snapshots": [], "instances": {name: value["instance"]}}).get(name)
