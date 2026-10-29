import json
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Any

from infrawrench_bulk_instances import AWSPricingDataError, download_aws_ec2_pricing_data

base_url, cache_path, token, cache = sys.argv[1:5]


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


def row(r: Any) -> dict[str, Any]:
    return {CAMEL.get(k, k): (ts(v) if isinstance(v, datetime) else v) for k, v in asdict(r).items()}


try:
    data = download_aws_ec2_pricing_data(
        base_url=base_url,
        cache_path=cache_path,
        cache_pricing_data=cache == "1",
        token=None if token == "-" else token,
    )
except AWSPricingDataError as e:
    print(json.dumps({"error": {"status": e.status, "message": str(e)}}))
    sys.exit(3)

regions = {k: dict(v) for k, v in data.regions.items()}
missing = data.get("nope")
out: dict[str, Any] = {
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
    p, h = i.pricing, i.pricing_history
    out["instances"][k] = {
        "name": i.name,
        "createdAt": ts(i.created_at),
        "deletedAt": ts(i.deleted_at),
        "attributes": dict(i.attributes),
        "attributesIn": {r: i.attributes_in(r) for r in [*regions, "Mystery", "Nowhere"]},
        "attributesHistory": [row(c) for c in i.attributes_history],
        "pricing": {"onDemand": [row(r) for r in p.on_demand], "reserved": [row(r) for r in p.reserved]},
        "pricingHistory": {"onDemand": [row(r) for r in h.on_demand], "reserved": [row(r) for r in h.reserved]},
    }
print(json.dumps(out, indent=1))
