"""Writes small bundles that exercise every decoding rule.

fixture/bundle-<NAME>.json(.xz) and fixture/latest are an EC2 bundle. fixture/rds-bundle-<NAME>.json(.xz) and
fixture/rds-latest are an RDS one, which names its own variant keys. fixture/api/<platform>/<instance>.json is each
instance as the Infrawrench API serves it from `/api/v1/aws-bulk-pricing/<platform>/<instance>`.
"""
import json, lzma, os, sys

NAME = "20261001T000000Z"
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, "fixture")
os.makedirs(out, exist_ok=True)

table = []
def s(x):
    if x not in table:
        table.append(x)
    return table.index(x)

t1, t2, t3, t4 = 1700000000, 1710000000, 1720000000, 1730000000
USE, EU, SAO, LZ, MYST = (s(r) for r in ["US East (N. Virginia)", "EU (Ireland)", "South America (São Paulo)", "Local Zone X", "Mystery"])

bundle = {
    "compression_table": table,
    "snapshots": [t1, t2, t3, t4],
    "regions": [
        [USE, [[s("regionCode"), s("us-east-1")], [s("locationType"), s("AWS Region")]]],
        [EU, [[s("regionCode"), s("eu-west-1")], [s("locationType"), s("AWS Region")]]],
        [SAO, [[s("regionCode"), s("sa-east-1")], [s("locationType"), s("AWS Region")]]],
        # No regionCode; "Mystery" has no entry at all.
        [LZ, [[s("locationType"), s("AWS Local Zone")]]],
    ],
    "variants": [
        [s("Linux"), s("Shared"), s("No License required"), s("NA"), s("Used")],
        [s("Windows"), s("Shared"), s("License Included"), s("NA"), s("Used")],
        [s("Linux"), s("Dedicated"), s("No License required"), s("SQL Std"), s("Used")],
    ],
    "reserved_terms": [
        [s("1yr"), s("standard"), s("No Upfront")],
        [s("3yr"), s("convertible"), s("All Upfront")],
    ],
    "instances": {},
}

bundle["instances"]["m5.large"] = [
    [[s("vcpu"), s("2")], [s("memory"), s("8 GiB")], [s("family"), s("General purpose")]],
    [
        [t3, s("memory"), s("8.0 GiB"), None],
        [t2, s("family"), None],                      # removed globally (short row)...
        [t2, s("family"), s("General Purpose")],      # ...and re-added at the same instant: later row wins
        [t2, s("network"), s("Up to 10 Gigabit"), USE],
        [t3, s("network"), s("10 Gigabit")],          # newer global change; USE override still applies
        [t3, s("vcpu"), None, EU],                    # regional removal
        [t4, s("note"), s("café ☕"), SAO],
        [t1, s("gpu"), s("0")],
    ],
    0.096,
    [
        [t1, USE, 0],                 # base price
        [t1, EU, 0, 0.107],
        [t3, USE, 0, 0.1],
        [t2, USE, 1, 0.188],
        [t4, USE, 1, None],           # no longer offered
        [t1, MYST, 0],                # region with no regions entry
        [t2, LZ, 2, 0.5],             # region with no regionCode
        [t3, EU, 0, 0.11],
        [t3, EU, 0, 0.12],            # same instant: later row wins
        [t2, SAO, 0, 1],              # integer price
    ],
    [
        [t1, USE, 0, 0, 0.06],
        [t1, USE, 0, 1, 0, 1500.5],   # integer 0 hourly, upfront
        [t3, USE, 0, 0, 0.055, 10],
        [t4, USE, 0, 1, None],        # no longer offered
        [t2, EU, 0, 0, 0.07],
        [t2, LZ, 2, 1, 0.3, 0],
    ],
    t1,
    None,
]
bundle["instances"]["t2.micro"] = [
    [[s("vcpu"), s("1")], [s("memory"), s("1 GiB")]],
    [],
    0.0116,
    [[t1, USE, 0], [t3, USE, 0, None]],
    [[t1, USE, 0, 0, 0.007], [t3, USE, 0, 0, None]],
    t1,
    t3,
]
bundle["instances"]["x1.weird"] = [[], [], 2, [[t2, USE, 0]], [], t2, None]

def write(prefix, bundle):
    text = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out, f"{prefix}bundle-{NAME}.json"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(out, f"{prefix}bundle-{NAME}.json.xz"), "wb") as f:
        f.write(lzma.compress(text.encode("utf-8"), format=lzma.FORMAT_XZ))
    with open(os.path.join(out, f"{prefix}latest"), "w") as f:
        f.write(NAME + "\n")


class Counter:
    """Counts index uses, then renumbers them most used first (ties keep their old order)."""
    def __init__(self):
        self.counts = {}
    def add(self, *indices):
        for i in indices:
            self.counts[i] = self.counts.get(i, 0) + 1
    def order(self):
        return sorted(self.counts, key=lambda i: (-self.counts[i], i))
    def renumber(self):
        return {old: new for new, old in enumerate(self.order())}

def reduce_instance(bundle, platform, offer, variant_keys, name):
    """One instance with the bundle's tables cut down to what it uses, as the Infrawrench API's sync
    (app/packages/web/src/aws-bulk-pricing/format.ts in Infrawrench) writes it."""
    attrs, changes, base, od, rs, created, deleted = bundle["instances"][name]
    strings, variants, terms, locations = Counter(), Counter(), Counter(), set()
    for k, v in attrs:
        strings.add(k, v)
    # The bundler always writes [ts, key, value|null(, region)]; the fixture also has the shorter forms decoders accept.
    changes = [[c[0], c[1], c[2] if len(c) > 2 else None] + ([c[3]] if len(c) > 3 and c[3] is not None else []) for c in changes]
    for c in changes:
        strings.add(c[1])
        if c[2] is not None:
            strings.add(c[2])
        if len(c) > 3:
            strings.add(c[3])
            locations.add(c[3])
    for r in od:
        strings.add(r[1])
        locations.add(r[1])
        variants.add(r[2])
    for r in rs:
        strings.add(r[1])
        locations.add(r[1])
        variants.add(r[2])
        terms.add(r[3])
    for v in variants.counts:
        strings.add(*bundle["variants"][v])
    for t in terms.counts:
        strings.add(*bundle["reserved_terms"][t])
    regions = [r for r in bundle["regions"] if r[0] in locations]
    for _, pairs in regions:
        for k, v in pairs:
            strings.add(k, v)
    S, V, T = strings.renumber(), variants.renumber(), terms.renumber()
    return {
        "compression_table": [bundle["compression_table"][i] for i in strings.order()],
        "platform": platform,
        "offer": offer,
        "name": name,
        "variant_keys": variant_keys,
        "regions": [[S[loc], [[S[k], S[v]] for k, v in pairs]] for loc, pairs in regions],
        "variants": [[S[i] for i in bundle["variants"][v]] for v in variants.order()],
        "reserved_terms": [[S[i] for i in bundle["reserved_terms"][t]] for t in terms.order()],
        "instance": [
            [[S[k], S[v]] for k, v in attrs],
            [[c[0], S[c[1]], None if c[2] is None else S[c[2]]] + [S[i] for i in c[3:]] for c in changes],
            base,
            [[r[0], S[r[1]], V[r[2]], *r[3:]] for r in od],
            [[r[0], S[r[1]], V[r[2]], T[r[3]], *r[4:]] for r in rs],
            created,
            deleted,
        ],
    }

def write_api(platform, bundle):
    offer = bundle.get("offer", "AmazonEC2")
    variant_keys = bundle.get("variant_keys", ["operatingSystem", "tenancy", "licenseModel", "preInstalledSw", "capacitystatus"])
    os.makedirs(os.path.join(out, "api", platform), exist_ok=True)
    for name in bundle["instances"]:
        value = reduce_instance(bundle, platform, offer, variant_keys, name)
        with open(os.path.join(out, "api", platform, f"{name}.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")))

write("", bundle)
write_api("ec2", bundle)

# RDS: variants are named by variant_keys, and several share a region, so prices must be told apart
# by every variant field. licenseModel is also one of EC2's fields.
table = []
USE, EU = s("US East (N. Virginia)"), s("EU (Ireland)")
MYSQL, MULTI = s("MySQL"), s("Multi-AZ")
rds = {
    "offer": "AmazonRDS",
    "compression_table": table,
    "snapshots": [t1, t2, t3],
    "regions": [
        [USE, [[s("regionCode"), s("us-east-1")]]],
        [EU, [[s("regionCode"), s("eu-west-1")]]],
    ],
    "variant_keys": ["databaseEngine", "licenseModel", "deploymentOption", "usagetype"],
    "variants": [
        [MYSQL, s("No license required"), s("Single-AZ"), s("InstanceUsage")],
        [MYSQL, s("No license required"), MULTI, s("Multi-AZUsage")],
        [s("PostgreSQL"), s("No license required"), s("Single-AZ"), s("InstanceUsage")],
    ],
    "reserved_terms": [[s("1yr"), s("standard"), s("All Upfront")]],
    "instances": {
        "db.m5.large": [
            [[s("vcpu"), s("2")], [s("memory"), s("8 GiB")]],
            [[t2, s("memory"), s("8.0 GiB")]],
            0.171,
            [
                [t1, USE, 0],
                [t1, USE, 1, 0.342],
                [t1, USE, 2, 0.178],
                [t2, USE, 1, 0.35],
                [t1, EU, 0, 0.19],
                [t1, EU, 2, 0.2],
                [t3, EU, 2, None],    # no longer offered; EU MySQL Single-AZ still is
            ],
            [
                [t1, USE, 0, 0, 0, 1000],
                [t1, USE, 1, 0, 0, 2000],
                [t2, USE, 0, 0, 0, 950],
            ],
            t1,
            None,
        ],
        "db.t3.micro": [[[s("vcpu"), s("2")]], [], 0.017, [[t1, USE, 0], [t1, USE, 1, 0.034]], [], t1, None],
    },
}
write("rds-", rds)
write_api("rds", rds)
print(out)
