# Conformance suite

Every SDK must decode the same bundles to the same values and handle downloads, caching and
errors the same way. `suite.py` serves `fixture/` from a fake bundles server, runs one SDK's dump
program through each scenario, and compares its output with `reference.json`, which is the
TypeScript SDK's output.

```sh
conformance/run.sh <typescript|python|ruby|java|csharp|rust|php|go>
```

`make_fixture.py` regenerates `fixture/`: an EC2 bundle, and an RDS one served as `rds-latest` and
`rds-bundle-<name>.json.xz`, and each of their instances as the Infrawrench API serves it
(`fixture/api/<platform>/<instance>.json`, the bundle's tables cut down to what the instance uses). Every SDK must
decode those to the same values as the whole bundle. After changing it, regenerate `reference.json` and
`reference-rds.json` from the TypeScript SDK (offline, from a cache seeded with the fixture):

```sh
mkdir -p /tmp/seed && cp conformance/fixture/*bundle-*.json /tmp/seed/
node conformance/dumps/typescript/dump.mjs http://127.0.0.1:9 /tmp/seed test-token 1 > conformance/reference.json
node conformance/dumps/typescript/dump.mjs http://127.0.0.1:9 /tmp/seed test-token 1 rds > conformance/reference-rds.json
```

## Dump program contract

Invoked as `<program> <baseUrl> <cacheDir> <token> <cache> [platform [instance]]`:

- `token` is `-` to pass no token (so the SDK falls back to `INFRAWRENCH_API_KEY`).
- `cache` is `1` or `0` (`cachePricingData`).
- Without `platform`, load with the SDK's EC2 function; with it, load with the SDK's function that takes a
  platform, passing it through unchecked.
- With `instance`, fetch that one instance from the API at `baseUrl` with the SDK's function for it (`cacheDir` and
  `cache` are unused) and print `{"instance": <one entry of "instances" below, or null>}`, with `attributesIn` for
  the sorted regions in its `attributesHistory`, plus "Mystery" and "Nowhere".

On success print one JSON object to stdout and exit 0. On the SDK's AWSPricingDataError print
`{"error": {"status": <HTTP status or null>, "message": "..."}}` and exit 3. Any other failure: exit non-zero.

Dates are Unix seconds (integers). A missing `regionCode` is `null`. Everything comes from the SDK's
public API only:

```
{
  "offer": "AmazonEC2",
  "variantKeys": ["operatingSystem", ...],
  "snapshots": [ts, ...],
  "regions": { "<location>": { "<key>": "<value>" } },
  "keys": [sorted instance types],
  "has": { "m5.large": bool, "nope": bool },
  "getMissing": null,                      // get("nope")
  "instances": {
    "<type>": {
      "name": "...", "createdAt": ts, "deletedAt": ts|null,
      "attributes": {...},
      "attributesIn": { "<loc>": {...} },  // for every location in regions, plus "Mystery" and "Nowhere"
      "attributesHistory": [ {"at", "key", "value"|null, "region"|null} ],   // SDK order
      "pricing": {
        "onDemand": [ {"region", "regionCode", "variant": {<variant key>: value}, "operatingSystem", "tenancy", "licenseModel", "preInstalledSw", "capacitystatus", "hourly", "since"} ],
        "reserved": [ {...same location+variant..., "leaseContractLength", "offeringClass", "purchaseOption", "hourly", "upfront", "since"} ]
      },
      "pricingHistory": {
        "onDemand": [ {...location+variant..., "at", "hourly"|null} ],
        "reserved": [ {...location+variant+term..., "at", "hourly"|null, "upfront"|null} ]
      }
    }
  }
}
```

List order is compared exactly; object key order is not.
