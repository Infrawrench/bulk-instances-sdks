"""Writes small bundles that exercise every decoding rule.

fixture/bundle-<NAME>.json(.xz) and fixture/latest are an EC2 bundle. fixture/rds-bundle-<NAME>.json(.xz) and
fixture/rds-latest are an RDS one, which names its own variant keys. fixture/runpod-*, fixture/alibaba-*,
fixture/azure-*, fixture/gcp-*, fixture/hetzner-*, fixture/hetznerauction-*, fixture/ovh-*, fixture/ovheco-*, fixture/oracle-* and
fixture/ibm-* are bundles for other clouds. fixture/api/<platform>/<instance>.json is each
instance, of every platform the Infrawrench API serves, as it serves it from `/api/v1/aws-bulk-pricing/<platform>/<instance>`.
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

# Other clouds, as other-instances (instances-bundler's other/) writes them. They carry source_version, a key
# AWS bundles don't have, which every decoder must skip. The Infrawrench API serves their instances the same way
# as AWS ones (without source_version); RunPod's ids have spaces, which the SDKs must escape.

# RunPod: one variant key, every price in "global", savings plans as reserved rows with no upfront.
table = []
G, DC = s("global"), s("US-TX-1")
SEC, COM = s("Secure Cloud"), s("Community Cloud")
runpod = {
    "offer": "RunpodPods",
    "compression_table": table,
    "snapshots": [t1, t2, t3],
    "regions": [
        [DC, [[s("location"), s("United States")], [s("locationType"), s("Data Center")], [s("regionCode"), DC]]],
        [G, [[s("locationType"), s("Global")], [s("regionCode"), G]]],
    ],
    "variant_keys": ["cloudType"],
    "variants": [[SEC], [COM]],
    "reserved_terms": [[s("3mo"), s("Savings Plan"), s("All Upfront")], [s("6mo"), s("Savings Plan"), s("All Upfront")]],
    "instances": {
        "NVIDIA H100 80GB HBM3": [
            [[s("dataCenters"), DC], [s("displayName"), s("H100 SXM")], [s("memoryInGb"), s("80")],
             [s("priceUnit"), s("GPU-Hour")], [s("productFamily"), s("GPU")]],
            [[t2, s("dataCenters"), s("EU-RO-1,US-TX-1")]],
            2.69,
            [[t1, G, 1], [t1, G, 0, 3.99], [t2, G, 0, 2.99], [t3, G, 1, None]],
            [[t1, G, 0, 0, 3.49], [t1, G, 0, 1, 3.29], [t2, G, 0, 0, 2.89]],
            t1,
            None,
        ],
        "cpu3c-2-4": [
            [[s("memoryInGb"), s("4")], [s("priceUnit"), s("Hour")], [s("productFamily"), s("CPU")], [s("vcpu"), s("2")]],
            [],
            0.06,
            [[t1, G, 0], [t3, G, 0, None]],
            [],
            t1,
            t3,
        ],
    },
}
write("runpod-", runpod)
write_api("runpod", runpod)

# Alibaba Cloud ECS: region ids as locations, two variant keys (one of them EC2's operatingSystem),
# subscriptions as All Upfront rows (hourly 0) and reserved instances with both parts.
table = []
HZ, USE = s("cn-hangzhou"), s("us-east-1")
LINUX_VPC, WIN_VPC, LINUX_CLASSIC = 0, 1, 2
alibaba = {
    "offer": "AlibabaECS",
    "source_version": "2.0.426",
    "compression_table": table,
    "snapshots": [t1, t2],
    "regions": [
        [HZ, [[s("locationType"), s("Alibaba Cloud Region")], [s("name"), s("China (Hangzhou)")], [s("regionCode"), HZ]]],
        [USE, [[s("locationType"), s("Alibaba Cloud Region")], [s("name"), s("US (Virginia)")], [s("regionCode"), USE]]],
    ],
    "variant_keys": ["operatingSystem", "networkType"],
    "variants": [[s("Linux"), s("VPC")], [s("Windows"), s("VPC")], [s("Linux"), s("Classic")]],
    "reserved_terms": [
        [s("1yr"), s("Subscription"), s("All Upfront")],
        [s("1mo"), s("Subscription"), s("All Upfront")],
        [s("3yr"), s("Reserved Instance"), s("Partial Upfront")],
    ],
    "instances": {
        "ecs.g6.large": [
            [[s("CpuCoreCount"), s("2")], [s("CpuOptions.ThreadsPerCore"), s("2")], [s("MemorySize"), s("8.0")],
             [s("SupportedBootModes.SupportedBootMode"), s("BIOS,UEFI")]],
            [[t2, s("MemorySize"), s("16.0")]],
            0.1068,
            [[t1, HZ, LINUX_VPC], [t1, HZ, LINUX_CLASSIC], [t1, USE, LINUX_VPC, 0.12], [t1, USE, WIN_VPC, 0.2],
             [t2, HZ, LINUX_CLASSIC, None]],
            [[t1, HZ, LINUX_VPC, 0, 0, 500.5], [t1, HZ, LINUX_VPC, 1, 0, 50], [t1, HZ, LINUX_CLASSIC, 0, 0, 480],
             [t1, USE, WIN_VPC, 2, 0.05, 300], [t2, USE, WIN_VPC, 2, 0.04, 250], [t2, HZ, LINUX_CLASSIC, 0, None]],
            t1,
            None,
        ],
    },
}
write("alibaba-", alibaba)
write_api("alibaba", alibaba)

# Azure: ARM region names as locations, operatingSystem and priority as variant keys, reservations as All Upfront
# rows (hourly 0) and savings plans as No Upfront rows (upfront left out), a size with no calculator specs.
table = []
EUS, WEU = s("eastus"), s("westeurope")
LINUX_REG, WIN_REG, LINUX_SPOT, WIN_LOW = 0, 1, 2, 3
azure = {
    "offer": "AzureVM",
    "compression_table": table,
    "snapshots": [t1, t2],
    "regions": [
        [EUS, [[s("locationType"), s("Azure Region")], [s("name"), s("US East")], [s("regionCode"), EUS]]],
        [WEU, [[s("locationType"), s("Azure Region")], [s("name"), s("EU West")], [s("regionCode"), WEU]]],
    ],
    "variant_keys": ["operatingSystem", "priority"],
    "variants": [[s("Linux"), s("Regular")], [s("Windows"), s("Regular")], [s("Linux"), s("Spot")], [s("Windows"), s("Low Priority")]],
    "reserved_terms": [
        [s("1yr"), s("Reserved Instance"), s("All Upfront")],
        [s("1yr"), s("Savings Plan"), s("No Upfront")],
        [s("3yr"), s("Savings Plan"), s("No Upfront")],
    ],
    "instances": {
        "Standard_D2s_v3": [
            [[s("cores"), s("2")], [s("diskSize"), s("16")], [s("isVcpu"), s("true")], [s("productFamily"), s("Virtual Machines")],
             [s("productName"), s("Virtual Machines DSv3 Series")], [s("ram"), s("8.0")], [s("series"), s("Dsv3")], [s("skuName"), s("D2s v3")]],
            [],
            0.096,
            [[t1 - 86400 * 365, EUS, LINUX_REG], [t1 - 86400 * 365, EUS, WIN_REG, 0.188], [t1, EUS, LINUX_SPOT, 0.01919],
             [t1, EUS, WIN_LOW, 0.075], [t1, WEU, LINUX_REG, 0.12], [t2, EUS, LINUX_SPOT, 0.0215]],
            [[t1, EUS, LINUX_REG, 0, 0, 500], [t1, EUS, LINUX_REG, 1, 0.06624], [t1, EUS, LINUX_REG, 2, 0.04512],
             [t2, EUS, LINUX_REG, 0, None]],
            t1,
            None,
        ],
        "Standard_D2pds_v7": [
            [[s("productFamily"), s("Virtual Machines")], [s("skuName"), s("D2pds v7")]],
            [[t2, s("productName"), s("Virtual Machines Dpdsv7 Series"), EUS]],
            0.08,
            [[t2, EUS, LINUX_REG]],
            [],
            t2,
            None,
        ],
    },
}
write("azure-", azure)

# Google Cloud Compute Engine: region names as locations, provisioningModel as the one variant key, committed use
# discounts as No Upfront rows, each region's zones as a regional attribute override, a machine type that goes away.
table = []
USC, EUW = s("us-central1"), s("europe-west1")
STD, SPOT = 0, 1
gcp = {
    "offer": "GCPCompute",
    "compression_table": table,
    "snapshots": [t1, t2, t3],
    "regions": [
        [EUW, [[s("locationType"), s("Google Cloud Region")], [s("regionCode"), EUW]]],
        [USC, [[s("locationType"), s("Google Cloud Region")], [s("regionCode"), USC]]],
    ],
    "variant_keys": ["provisioningModel"],
    "variants": [[s("Standard")], [s("Spot")]],
    "reserved_terms": [[s("1yr"), s("Committed Use"), s("No Upfront")], [s("3yr"), s("Committed Use"), s("No Upfront")]],
    "instances": {
        "n2-standard-2": [
            [[s("description"), s("2 vCPUs 8 GB RAM")], [s("guestCpus"), s("2")], [s("isSharedCpu"), s("false")],
             [s("memoryMb"), s("8192")], [s("productFamily"), s("Compute Engine")], [s("zones"), s("us-central1-a,us-central1-b")]],
            [[t1, s("zones"), s("europe-west1-b,europe-west1-c"), EUW], [t3, s("zones"), s("us-central1-a"), USC]],
            0.097118,
            [[t1, USC, STD], [t1, USC, SPOT, 0.058256], [t1, EUW, STD, 0.106836], [t2, USC, SPOT, 0.0571]],
            [[t1, USC, STD, 0, 0.061182], [t1, USC, STD, 1, 0.043706]],
            t1,
            None,
        ],
        "a2-highgpu-1g": [
            [[s("acceleratorCount"), s("1")], [s("acceleratorType"), s("nvidia-tesla-a100")], [s("guestCpus"), s("12")],
             [s("memoryMb"), s("87040")], [s("productFamily"), s("Compute Engine")], [s("zones"), s("us-central1-a")]],
            [],
            3.673385,
            [[t1, USC, STD], [t1, USC, SPOT, 1.98913], [t3, USC, STD, None], [t3, USC, SPOT, None]],
            [[t1, USC, STD, 0, 2.31420704], [t3, USC, STD, 0, None]],
            t1,
            t3,
        ],
    },
}
write("gcp-", gcp)

# Hetzner cloud servers: location names as regions, with or without the primary IPv4 as the variant, the monthly cap as a
# Postpaid term (hourly 0, upfront the cap), and a server type with a different price in one location.
table = []
FSN, ASH = s("fsn1"), s("ash")
IPV6, IPV4 = 0, 1
CAP = 0
hetzner = {
    "offer": "HetznerCloud",
    "compression_table": table,
    "snapshots": [t1, t2],
    "regions": [
        [ASH, [[s("country"), s("us")], [s("locationType"), s("Hetzner Location")], [s("name"), s("Ashburn, VA")], [s("regionCode"), ASH]]],
        [FSN, [[s("country"), s("de")], [s("locationType"), s("Hetzner Location")], [s("name"), s("Falkenstein")], [s("regionCode"), FSN]]],
    ],
    "variant_keys": ["ipv4"],
    "variants": [[s("IPv6 only")], [s("Primary IPv4")]],
    "reserved_terms": [[s("1mo"), s("Monthly Cap"), s("Postpaid")]],
    "instances": {
        "cx23": [
            [[s("architecture"), s("x86_64")], [s("category"), s("Cost-Optimized")], [s("cores"), s("2")], [s("memoryInGb"), s("4")], [s("name"), s("CX23")], [s("productFamily"), s("Cloud Server")]],
            [],
            0.0104,
            [[t1, FSN, IPV6], [t1, FSN, IPV4, 0.0114], [t1, ASH, IPV6, 0.0129], [t2, FSN, IPV4, 0.012]],
            [[t1, FSN, IPV6, CAP, 0, 6.49], [t1, FSN, IPV4, CAP, 0, 7.09], [t1, ASH, IPV6, CAP, 0, 8.09]],
            t1,
            None,
        ],
    },
}
write("hetzner-", hetzner)

# Hetzner Server Auction: listing ids as instances, one price cut, and a listing that sold.
table = []
FSN = s("fsn1")
IPV6, IPV4 = 0, 1
CAP = 0
hetznerauction = {
    "offer": "HetznerAuction",
    "compression_table": table,
    "snapshots": [t1, t2, t3],
    "regions": [[FSN, [[s("locationType"), s("Hetzner Location")], [s("name"), s("Falkenstein")], [s("regionCode"), FSN]]]],
    "variant_keys": ["ipv4"],
    "variants": [[s("IPv6 only")], [s("Primary IPv4")]],
    "reserved_terms": [[s("1mo"), s("Monthly Cap"), s("Postpaid")]],
    "instances": {
        "3107671": [
            [[s("CPU.Name"), s("Intel Core i7-7700")], [s("RAM.Size"), s("64")], [s("datacenter"), s("FSN1-DC4")], [s("fixedPrice"), s("false")], [s("productFamily"), s("Dedicated Server")]],
            [],
            0.1362,
            [[t1, FSN, IPV6], [t1, FSN, IPV4, 0.1392], [t2, FSN, IPV6, 0.13]],
            [[t1, FSN, IPV6, CAP, 0, 85], [t1, FSN, IPV4, CAP, 0, 86.9], [t2, FSN, IPV6, CAP, 0, 81]],
            t1,
            None,
        ],
        "3082226": [
            [[s("CPU.Name"), s("AMD Ryzen 5 3600")], [s("RAM.Size"), s("64")], [s("datacenter"), s("FSN1-DC21")], [s("fixedPrice"), s("true")], [s("productFamily"), s("Dedicated Server")]],
            [],
            0.2099,
            [[t1, FSN, IPV6], [t3, FSN, IPV6, None]],
            [[t1, FSN, IPV6, CAP, 0, 131], [t3, FSN, IPV6, CAP, None]],
            t1,
            t3,
        ],
    },
}
write("hetznerauction-", hetznerauction)

# OVHcloud Public Cloud: pricing zones as regions, operatingSystem as the variant, global attributes, and monthly terms
# both postpaid and paid at the start of the month.
table = []
WORLD, AF, US = s("world"), s("lz-af"), s("us")
LIN, WIN = 0, 1
POST, UP = 0, 1
ovh = {
    "offer": "OVHPublicCloud",
    "compression_table": table,
    "snapshots": [t1, t2],
    "regions": [
        [AF, [[s("locationType"), s("OVHcloud Pricing Zone")], [s("name"), s("Local Zones in Africa")], [s("regionCode"), AF]]],
        [US, [[s("locationType"), s("OVHcloud Pricing Zone")], [s("name"), s("OVHcloud US regions")], [s("regionCode"), US]]],
        [WORLD, [[s("locationType"), s("OVHcloud Pricing Zone")], [s("name"), s("Standard regions")], [s("regionCode"), WORLD]]],
    ],
    "variant_keys": ["operatingSystem"],
    "variants": [[s("Linux")], [s("Windows")]],
    "reserved_terms": [[s("1mo"), s("Monthly"), s("Postpaid")], [s("1mo"), s("Monthly"), s("All Upfront")]],
    "instances": {
        "b2-7": [
            [[s("brick"), s("guaranteed-resources")], [s("cpu.cores"), s("2")], [s("memory.size"), s("7")], [s("productFamily"), s("Public Cloud Instance")]],
            [],
            0.0837,
            [[t1, WORLD, LIN], [t1, WORLD, WIN, 0.2251], [t1, AF, LIN, 0.105], [t1, US, LIN, 0.0879], [t2, AF, LIN, 0.11]],
            [[t1, WORLD, LIN, POST, 0, 50.5], [t1, US, LIN, UP, 0, 52]],
            t1,
            None,
        ],
    },
}
write("ovh-", ovh)

# OVHcloud eco: data centers as regions, three variant keys of which the last is often empty, a regional attribute,
# and no on-demand rows at all: these servers are rented by the month, so the rent is a term, and the base price is 0.
table = []
GRA, SGP = s("gra"), s("sgp")
EMPTY = s("")
RAM32, RAM64 = s("ram-32g-ecc-2666"), s("ram-64g-ecc-2666")
RAID = s("softraid-2x4000sa")
SMALL, BIG = 0, 1
RENT, YEAR, TWO = 0, 1, 2
ovheco = {
    "offer": "OVHEco",
    "compression_table": table,
    "snapshots": [t1, t2],
    "regions": [
        [GRA, [[s("locationType"), s("OVHcloud Data Center")], [s("name"), s("Gravelines")], [s("regionCode"), GRA]]],
        [SGP, [[s("locationType"), s("OVHcloud Data Center")], [s("name"), s("Singapore")], [s("regionCode"), SGP]]],
    ],
    "variant_keys": ["memory", "storage", "systemStorage"],
    "variants": [[RAM32, RAID, EMPTY], [RAM64, RAID, EMPTY]],
    "reserved_terms": [[s("1mo"), s("Rental"), s("All Upfront")], [s("1yr"), s("Prepaid"), s("All Upfront")], [s("2yr"), s("Prepaid"), s("All Upfront")]],
    "instances": {
        "24sys01": [
            [[s("billing"), s("Monthly")], [s("cpu.cores"), s("6")], [s("planCode"), s("24sys01-v1")], [s("productFamily"), s("Dedicated Server")], [s("range"), s("soyoustart")], [s("setupFee"), s("33.2")]],
            [[t1, s("planCode"), s("24sys01-v1-sgp"), SGP]],
            0,
            [],
            [[t1, GRA, SMALL, RENT, 0, 33.2], [t1, GRA, BIG, RENT, 0, 44.3], [t1, GRA, SMALL, YEAR, 0, 378.48], [t1, GRA, SMALL, TWO, 0, 756.96],
             [t1, SGP, SMALL, RENT, 0, 40], [t2, GRA, SMALL, RENT, 0, 35]],
            t1,
            None,
        ],
    },
}
write("ovheco-", ovheco)

# Oracle: one global region, operatingSystem as the variant, a flexible size with its rates as attributes, a GPU shape.
table = []
GLOBAL = s("global")
LIN, WIN = 0, 1
oracle = {
    "offer": "OracleCompute",
    "compression_table": table,
    "snapshots": [t1, t2],
    "regions": [[GLOBAL, [[s("locationType"), s("Global")], [s("regionCode"), GLOBAL]]]],
    "variant_keys": ["operatingSystem"],
    "variants": [[s("Linux")], [s("Windows")]],
    "reserved_terms": [],
    "instances": {
        "VM.Standard.E5.Flex-2-16": [
            [[s("flexible"), s("true")], [s("memoryGbPrice"), s("0.002")], [s("memoryInGb"), s("16")], [s("ocpuPrice"), s("0.03")], [s("ocpus"), s("2")], [s("shape"), s("VM.Standard.E5.Flex")]],
            [],
            0.092,
            [[t1, GLOBAL, LIN], [t1, GLOBAL, WIN, 0.276]],
            [],
            t1,
            None,
        ],
        "BM.GPU.H100.8": [
            [[s("gpuCount"), s("8")], [s("memoryInGb"), s("2048")], [s("ocpus"), s("112")], [s("shape"), s("BM.GPU.H100.8")]],
            [],
            80,
            [[t1, GLOBAL, LIN], [t2, GLOBAL, LIN, 72]],
            [],
            t1,
            None,
        ],
    },
}
write("oracle-", oracle)

# IBM: regions, capacityType as the variant (Spot and burstable beside on-demand), reservations with an hourly rate and no
# upfront price.
table = []
DAL, SYD = s("us-south"), s("au-syd")
OD, SPOT, BURST = 0, 1, 2
Y1, Y3 = 0, 1
ibm = {
    "offer": "IBMVPC",
    "compression_table": table,
    "snapshots": [t1, t2],
    "regions": [
        [SYD, [[s("locationType"), s("IBM Cloud Region")], [s("name"), s("Sydney")], [s("regionCode"), SYD]]],
        [DAL, [[s("locationType"), s("IBM Cloud Region")], [s("name"), s("Dallas")], [s("regionCode"), DAL]]],
    ],
    "variant_keys": ["capacityType"],
    "variants": [[s("On-Demand")], [s("Spot")], [s("Burstable 50%")]],
    "reserved_terms": [[s("1yr"), s("Reserved"), s("No Upfront")], [s("3yr"), s("Reserved"), s("No Upfront")]],
    "instances": {
        "bxf-16x64": [
            [[s("cpu"), s("16")], [s("displayName"), s("Balanced Flex 16x64")], [s("family"), s("balanced")], [s("productFamily"), s("Virtual Server for VPC")], [s("ram"), s("64")]],
            [],
            0.941,
            [[t1, DAL, OD], [t1, DAL, SPOT, 0.235054], [t1, DAL, BURST, 0.63974], [t1, SYD, OD, 1.148], [t2, DAL, OD, 0.95]],
            [[t1, DAL, OD, Y1, 0.611], [t1, DAL, OD, Y3, 0.376]],
            t1,
            None,
        ],
    },
}
write("ibm-", ibm)
print(out)
