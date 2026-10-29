# Conformance suite

Every SDK must decode the same bundle to the same values and handle downloads, caching and
errors the same way. `suite.py` serves `fixture/` from a fake bundles server, runs one SDK's dump
program through each scenario, and compares its output with `reference.json`, which is the
TypeScript SDK's output.

```sh
conformance/run.sh <typescript|python|ruby|java|csharp|rust|php|go>
```

`make_fixture.py` regenerates `fixture/`. After changing it, regenerate `reference.json` from the
TypeScript SDK (offline, from a cache seeded with the fixture):

```sh
mkdir -p /tmp/seed && cp conformance/fixture/bundle-*.json /tmp/seed/
node conformance/dumps/typescript/dump.mjs http://127.0.0.1:9 /tmp/seed test-token 1 > conformance/reference.json
```

## Dump program contract

Invoked as `<program> <baseUrl> <cacheDir> <token> <cache>`:

- `token` is `-` to pass no token (so the SDK falls back to `INFRAWRENCH_API_KEY`).
- `cache` is `1` or `0` (`cachePricingData`).

On success print one JSON object to stdout and exit 0. On the SDK's AWSPricingDataError print
`{"error": {"status": <HTTP status or null>, "message": "..."}}` and exit 3. Any other failure: exit non-zero.

Dates are Unix seconds (integers). A missing `regionCode` is `null`. Everything comes from the SDK's
public API only:

```
{
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
        "onDemand": [ {"region", "regionCode", "operatingSystem", "tenancy", "licenseModel", "preInstalledSw", "capacitystatus", "hourly", "since"} ],
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
