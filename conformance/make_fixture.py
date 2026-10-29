"""Writes fixture/bundle-<NAME>.json(.xz) and fixture/latest: a small bundle that exercises every decoding rule."""
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

text = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
with open(os.path.join(out, f"bundle-{NAME}.json"), "w", encoding="utf-8") as f:
    f.write(text)
with open(os.path.join(out, f"bundle-{NAME}.json.xz"), "wb") as f:
    f.write(lzma.compress(text.encode("utf-8"), format=lzma.FORMAT_XZ))
with open(os.path.join(out, "latest"), "w") as f:
    f.write(NAME + "\n")
print(out)
