import json
import sys
from collections.abc import Mapping
from dataclasses import fields
from datetime import datetime
from typing import Any

from infrawrench_bulk_instances import (
    AlibabaInstance,
    AlibabaPricingData,
    AlibabaPricingDataError,
    AWSInstance,
    AWSPricingData,
    AWSPricingDataError,
    AzureInstance,
    AzurePricingData,
    AzurePricingDataError,
    GCPInstance,
    GCPPricingData,
    GCPPricingDataError,
    HetznerInstance,
    HetznerPricingData,
    HetznerPricingDataError,
    HetznerAuctionInstance,
    HetznerAuctionPricingData,
    HetznerAuctionPricingDataError,
    OVHInstance,
    OVHPricingData,
    OVHPricingDataError,
    OVHEcoInstance,
    OVHEcoPricingData,
    OVHEcoPricingDataError,
    OracleInstance,
    OraclePricingData,
    OraclePricingDataError,
    IBMInstance,
    IBMPricingData,
    IBMPricingDataError,
    RunpodInstance,
    RunpodPricingData,
    RunpodPricingDataError,
    download_alibaba_pricing_data,
    download_aws_ec2_pricing_data,
    download_aws_pricing_data,
    download_azure_pricing_data,
    download_gcp_pricing_data,
    download_hetzner_pricing_data,
    download_hetzner_auction_pricing_data,
    download_ovh_pricing_data,
    download_ovh_eco_pricing_data,
    download_oracle_pricing_data,
    download_ibm_pricing_data,
    download_runpod_pricing_data,
    fetch_alibaba_instance,
    fetch_aws_instance,
    fetch_runpod_instance,
)

base_url, cache_path, token, cache = sys.argv[1:5]
platform = sys.argv[5] if len(sys.argv) > 5 else None
instance_type = sys.argv[6] if len(sys.argv) > 6 else None


def ts(d: datetime | None) -> int | None:
    return None if d is None else int(d.timestamp())


CAMEL = {
    "region_code": "regionCode",
    "operating_system": "operatingSystem",
    "license_model": "licenseModel",
    "pre_installed_sw": "preInstalledSw",
    "lease_contract_length": "leaseContractLength",
    "offering_class": "offeringClass",
    "purchase_option": "purchaseOption",
}


def value(v: Any) -> Any:
    return ts(v) if isinstance(v, datetime) else dict(v) if isinstance(v, Mapping) else v


def row(r: Any) -> dict[str, Any]:
    return {CAMEL.get(f.name, f.name): value(getattr(r, f.name)) for f in fields(r)}


def instance(i: AWSInstance, region_names: list[str]) -> dict[str, Any]:
    p, h = i.pricing, i.pricing_history
    return {
        "name": i.name,
        "createdAt": ts(i.created_at),
        "deletedAt": ts(i.deleted_at),
        "attributes": dict(i.attributes),
        "attributesIn": {r: i.attributes_in(r) for r in [*region_names, "Mystery", "Nowhere"]},
        "attributesHistory": [row(c) for c in i.attributes_history],
        "pricing": {"onDemand": [row(r) for r in p.on_demand], "reserved": [row(r) for r in p.reserved]},
        "pricingHistory": {"onDemand": [row(r) for r in h.on_demand], "reserved": [row(r) for r in h.reserved]},
    }


def expect_error(e: AWSPricingDataError, provider_error: type[AWSPricingDataError]) -> None:
    if not isinstance(e, provider_error):
        print(f"expected a {provider_error.__name__}, got {type(e).__name__}", file=sys.stderr)
        sys.exit(1)


def expect_types(d: AWSPricingData, data_class: type[AWSPricingData], instance_class: type[AWSInstance]) -> None:
    keys = d.keys()
    if not isinstance(d, data_class) or (keys and not isinstance(d.get(keys[0]), instance_class)):
        print(f"expected {data_class.__name__} and {instance_class.__name__}", file=sys.stderr)
        sys.exit(1)


def expect_instance(i: AWSInstance | None, instance_class: type[AWSInstance]) -> None:
    if i is not None and not isinstance(i, instance_class):
        print(f"expected {instance_class.__name__}", file=sys.stderr)
        sys.exit(1)


if instance_type is not None:
    assert platform is not None
    api_token = None if token == "-" else token
    one: AWSInstance | None
    try:
        # RunPod and Alibaba have their own functions, returning their own instance type and errors.
        if platform == "runpod":
            try:
                one = fetch_runpod_instance(instance_type, base_url=base_url, token=api_token)
            except AWSPricingDataError as e:
                expect_error(e, RunpodPricingDataError)
                raise
            expect_instance(one, RunpodInstance)
        elif platform == "alibaba":
            try:
                one = fetch_alibaba_instance(instance_type, base_url=base_url, token=api_token)
            except AWSPricingDataError as e:
                expect_error(e, AlibabaPricingDataError)
                raise
            expect_instance(one, AlibabaInstance)
        else:
            one = fetch_aws_instance(platform, instance_type, base_url=base_url, token=api_token)
    except AWSPricingDataError as e:
        print(json.dumps({"error": {"status": e.status, "message": str(e)}}))
        sys.exit(3)
    # The regions its attributes are overridden in; every other one is the same as `attributes`.
    overridden = sorted({c.region for c in one.attributes_history if c.region is not None}) if one else []
    print(json.dumps({"instance": None if one is None else instance(one, overridden)}, indent=1))
    sys.exit(0)

try:
    options: dict[str, Any] = {
        "base_url": base_url,
        "cache_path": cache_path,
        "cache_pricing_data": cache == "1",
        "token": None if token == "-" else token,
    }
    # Clouds other than AWS have their own functions and types, and their own errors.
    data: AWSPricingData
    if platform == "runpod":
        try:
            data = download_runpod_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, RunpodPricingDataError)
            raise
        expect_types(data, RunpodPricingData, RunpodInstance)
    elif platform == "alibaba":
        try:
            data = download_alibaba_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, AlibabaPricingDataError)
            raise
        expect_types(data, AlibabaPricingData, AlibabaInstance)
    elif platform == "azure":
        try:
            data = download_azure_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, AzurePricingDataError)
            raise
        expect_types(data, AzurePricingData, AzureInstance)
    elif platform == "gcp":
        try:
            data = download_gcp_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, GCPPricingDataError)
            raise
        expect_types(data, GCPPricingData, GCPInstance)
    elif platform == "hetzner":
        try:
            data = download_hetzner_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, HetznerPricingDataError)
            raise
        expect_types(data, HetznerPricingData, HetznerInstance)
    elif platform == "hetznerauction":
        try:
            data = download_hetzner_auction_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, HetznerAuctionPricingDataError)
            raise
        expect_types(data, HetznerAuctionPricingData, HetznerAuctionInstance)
    elif platform == "ovh":
        try:
            data = download_ovh_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, OVHPricingDataError)
            raise
        expect_types(data, OVHPricingData, OVHInstance)
    elif platform == "ovheco":
        try:
            data = download_ovh_eco_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, OVHEcoPricingDataError)
            raise
        expect_types(data, OVHEcoPricingData, OVHEcoInstance)
    elif platform == "oracle":
        try:
            data = download_oracle_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, OraclePricingDataError)
            raise
        expect_types(data, OraclePricingData, OracleInstance)
    elif platform == "ibm":
        try:
            data = download_ibm_pricing_data(**options)
        except AWSPricingDataError as e:
            expect_error(e, IBMPricingDataError)
            raise
        expect_types(data, IBMPricingData, IBMInstance)
    else:
        data = download_aws_ec2_pricing_data(**options) if platform is None else download_aws_pricing_data(platform, **options)
except AWSPricingDataError as e:
    print(json.dumps({"error": {"status": e.status, "message": str(e)}}))
    sys.exit(3)

regions = {k: dict(v) for k, v in data.regions.items()}
missing = data.get("nope")
out: dict[str, Any] = {
    "offer": data.offer,
    "variantKeys": list(data.variant_keys),
    "snapshots": [ts(d) for d in data.snapshots],
    "regions": regions,
    "keys": sorted(data.keys()),
    "has": {"m5.large": data.has("m5.large"), "nope": "nope" in data},
    "getMissing": missing,
    "instances": {},
}
assert ("m5.large" in data) is data.has("m5.large")
for k in data.keys():
    i = data.get(k)
    assert i is not None and data.get(k) is i
    out["instances"][k] = instance(i, list(regions))
print(json.dumps(out, indent=1))
