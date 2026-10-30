import { downloadAwsEc2PricingData, downloadAwsPricingData, AWSPricingDataError } from "../../../ts/dist/index.js";

const [baseUrl, cachePath, token, cache, platform] = process.argv.slice(2);
const ts = (d) => (d === null ? null : d.getTime() / 1000);
const loc = (r) => ({ region: r.region, regionCode: r.regionCode ?? null });

let data;
try {
  const options = { baseUrl, cachePath, cachePricingData: cache === "1", ...(token === "-" ? {} : { token }) };
  data = platform === undefined ? await downloadAwsEc2PricingData(options) : await downloadAwsPricingData(platform, options);
} catch (e) {
  if (e instanceof AWSPricingDataError) {
    console.log(JSON.stringify({ error: { status: e.status ?? null, message: e.message } }));
    process.exit(3);
  }
  throw e;
}

const regions = Object.fromEntries([...data.regions].map(([k, v]) => [k, { ...v }]));
const out = {
  offer: data.offer,
  variantKeys: [...data.variantKeys],
  snapshots: data.snapshots.map(ts),
  regions,
  keys: data.keys().sort(),
  has: { "m5.large": data.has("m5.large"), nope: data.has("nope") },
  getMissing: data.get("nope") ?? null,
  instances: {},
};
for (const k of data.keys()) {
  const i = data.get(k);
  const p = i.pricing, h = i.pricingHistory;
  out.instances[k] = {
    name: i.name, createdAt: ts(i.createdAt), deletedAt: ts(i.deletedAt),
    attributes: { ...i.attributes },
    attributesIn: Object.fromEntries([...Object.keys(regions), "Mystery", "Nowhere"].map((r) => [r, i.attributesIn(r)])),
    attributesHistory: i.attributesHistory.map((c) => ({ ...c, at: ts(c.at) })),
    pricing: {
      onDemand: p.onDemand.map((r) => ({ ...r, ...loc(r), since: ts(r.since) })),
      reserved: p.reserved.map((r) => ({ ...r, ...loc(r), since: ts(r.since) })),
    },
    pricingHistory: {
      onDemand: h.onDemand.map((r) => ({ ...r, ...loc(r), at: ts(r.at) })),
      reserved: h.reserved.map((r) => ({ ...r, ...loc(r), at: ts(r.at) })),
    },
  };
}
console.log(JSON.stringify(out, null, 1));
