import { mkdir, readdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import xz from "xz-decompress";

const { XzReadableStream } = xz;

export type AWSPricingDataOptions = {
  /** Defines your Infrawrench API token. Defaults to the `INFRAWRENCH_API_KEY` environment variable. */
  token?: string;

  /** Whether to cache the pricing data. Defaults to true. */
  cachePricingData?: boolean;

  /** The cache path. Defaults to ~/.infrawrench/aws_pricing_data */
  cachePath?: string;

  /** Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com */
  baseUrl?: string;
};

const DEFAULT_BASE_URL = "https://instances-bundles.infrawrench.com";

/** Thrown when the pricing data cannot be downloaded. `status` is the HTTP status, if there was a response. */
export class AWSPricingDataError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "AWSPricingDataError";
    this.status = status;
  }
}

function get(url: string, token: string) {
  return fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      "User-Agent": "infrawrench/bulk-instances, typescript, 1.0",
    }
  });
}

/** GETs `url`, retrying the 503 the bundles Worker answers when it cannot reach the Infrawrench API. */
async function download(url: string, token: string): Promise<Response> {
  for (let attempt = 1; ; attempt++) {
    const res = await get(url, token);
    if (res.ok) return res;
    await res.body?.cancel();
    if (res.status === 401) {
      throw new AWSPricingDataError("The Infrawrench API did not accept the token (unknown, revoked or expired).", 401);
    }
    if (res.status !== 503 || attempt === 3) {
      throw new AWSPricingDataError(`GET ${url} failed with status ${res.status}.`, res.status);
    }
    const retryAfter = Number(res.headers.get("retry-after")) || 5;
    await new Promise((resolve) => setTimeout(resolve, retryAfter * 1000));
  }
}

/** The newest bundle already in the cache directory, if any. */
async function newestCached(cachePath: string): Promise<string | undefined> {
  const files = await readdir(cachePath).catch(() => []);
  return files.filter((f) => /^bundle-.+\.json$/.test(f)).sort().at(-1);
}

/**
 * Downloads the AWS EC2 pricing data compressed blob and decompresses it.
 *
 * The bucket's `latest` object names the newest bundle. With caching on, a bundle
 * is only downloaded when `latest` names one that is not in the cache yet, and if
 * `latest` cannot be fetched at all (offline, outage) the newest cached bundle is used.
 */
export async function downloadAwsEc2PricingData(options: AWSPricingDataOptions = {}): Promise<AWSPricingData> {
  const token = options.token ?? process.env.INFRAWRENCH_API_KEY;
  if (!token) {
    throw new AWSPricingDataError("No Infrawrench API token: pass `token` or set INFRAWRENCH_API_KEY.");
  }
  const baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
  const cache = options.cachePricingData ?? true;
  const cachePath = options.cachePath ?? join(homedir(), ".infrawrench", "aws_pricing_data");

  let name: string;
  try {
    const latest = (await (await download(`${baseUrl}/latest`, token)).text()).trim();
    if (!/^[A-Za-z0-9._-]+$/.test(latest)) {
      throw new AWSPricingDataError(`latest holds "${latest}", which is not a timestamp.`);
    }
    name = `bundle-${latest}.json`;
  } catch (err) {
    // A rejected token is a real answer; anything else falls back to what we already have.
    const cached = cache && !(err instanceof AWSPricingDataError && err.status === 401)
      ? await newestCached(cachePath)
      : undefined;
    if (!cached) throw err;
    name = cached;
  }

  // The cache holds the decompressed JSON: xz decompression is most of a load, reading the file is not.
  let json: string | undefined;
  if (cache) {
    json = await readFile(join(cachePath, name), "utf8").catch(() => undefined);
  }
  if (json === undefined) {
    const res = await download(`${baseUrl}/${name}.xz`, token);
    json = await new Response(new XzReadableStream(res.body!)).text();
    if (cache) {
      await mkdir(cachePath, { recursive: true });
      // Write then rename, so a crash mid-write never leaves a truncated bundle to be read next time.
      const tmp = join(cachePath, `${name}.${process.pid}.tmp`);
      await writeFile(tmp, json);
      await rename(tmp, join(cachePath, name));
      // Older bundles, including compressed ones cached by earlier versions of this SDK.
      for (const f of await readdir(cachePath)) {
        if (f !== name && /^bundle-.+\.json(\.xz)?$/.test(f)) await rm(join(cachePath, f), { force: true });
      }
    }
  }

  return new AWSPricingData(JSON.parse(json));
}

/** The bundle as instances-bundler writes it; every string is an index into `compression_table`. */
export type BundleFile = {
  compression_table: string[];
  snapshots: number[];
  regions: [number, [number, number][]][];
  variants: number[][];
  reserved_terms: number[][];
  instances: Record<string, RawInstance>;
};

type RawInstance = [
  attrs: [number, number][],
  attrChanges: (number | null)[][],
  basePrice: number,
  onDemand: (number | null)[][],
  reserved: (number | null)[][],
  createdAt: number,
  deletedAt: number | null,
];

/** The product fields that pick a price. */
export type Variant = {
  operatingSystem: string;
  tenancy: string;
  licenseModel: string;
  preInstalledSw: string;
  capacitystatus: string;
};

export type ReservedTerm = {
  leaseContractLength: string;
  offeringClass: string;
  purchaseOption: string;
};

type Location = {
  /** The AWS location name, e.g. `US East (N. Virginia)`. */
  region: string;
  /** e.g. `us-east-1`. Missing for locations the price list never gave a code. */
  regionCode?: string;
};

export type OnDemandPrice = Location & Variant & {
  /** USD per hour. */
  hourly: number;
  /** When this price took effect. */
  since: Date;
};

export type ReservedPrice = Location & Variant & ReservedTerm & {
  /** USD per hour. */
  hourly: number;
  /** USD paid up front. */
  upfront: number;
  since: Date;
};

export type Pricing = {
  onDemand: readonly OnDemandPrice[];
  reserved: readonly ReservedPrice[];
};

export type OnDemandPriceChange = Location & Variant & {
  at: Date;
  /** `null` means no longer offered from `at` on. */
  hourly: number | null;
};

export type ReservedPriceChange = Location & Variant & ReservedTerm & {
  at: Date;
  /** `null` means no longer offered from `at` on. */
  hourly: number | null;
  upfront: number | null;
};

export type PricingHistory = {
  /** Oldest first. */
  onDemand: readonly OnDemandPriceChange[];
  /** Oldest first. */
  reserved: readonly ReservedPriceChange[];
};

export type AttributeChange = {
  at: Date;
  key: string;
  /** `null` means the attribute was removed. */
  value: string | null;
  /** The AWS location this change applies to, or `null` for every region. */
  region: string | null;
};

const date = (ts: number) => new Date(ts * 1000);

/**
 * The AWS EC2 pricing data, keyed by instance type.
 *
 * Nothing is decoded until it is asked for: `get` wraps the raw rows, and each
 * getter on the returned {@link AWSInstance} decodes its part on first access
 * and keeps the result.
 */
export class AWSPricingData {
  #raw: BundleFile;
  #instances = new Map<string, AWSInstance>();
  #variants?: Variant[];
  #terms?: ReservedTerm[];
  #regions?: Map<string, Readonly<Record<string, string>>>;

  constructor(raw: BundleFile) {
    this.#raw = raw;
  }

  /** Every instance type in the bundle, including ones AWS no longer lists (see {@link AWSInstance.deletedAt}). */
  keys(): string[] {
    return Object.keys(this.#raw.instances);
  }

  has(instanceType: string): boolean {
    return Object.hasOwn(this.#raw.instances, instanceType);
  }

  /** The instance with this type (e.g. `m5.large`), or `undefined` if the bundle has never listed it. */
  get(instanceType: string): AWSInstance | undefined {
    let inst = this.#instances.get(instanceType);
    if (!inst && this.has(instanceType)) {
      inst = new AWSInstance(instanceType, this.#raw.instances[instanceType], this);
      this.#instances.set(instanceType, inst);
    }
    return inst;
  }

  /** The publication date of every AWS price list in the bundle, oldest first. */
  get snapshots(): Date[] {
    return this.#raw.snapshots.map(date);
  }

  /** Attributes of each AWS location (`regionCode`, `locationType`), keyed by location name. */
  get regions(): ReadonlyMap<string, Readonly<Record<string, string>>> {
    return (this.#regions ??= new Map(
      this.#raw.regions.map(([loc, pairs]) => [
        this.str(loc),
        Object.fromEntries(pairs.map(([k, v]) => [this.str(k), this.str(v)])),
      ]),
    ));
  }

  /** @internal */
  str(i: number): string {
    const s = this.#raw.compression_table[i];
    if (s === undefined) throw new Error(`string index ${i} out of range`);
    return s;
  }

  /** @internal */
  location(i: number): Location {
    const region = this.str(i);
    const regionCode = this.regions.get(region)?.regionCode;
    return regionCode === undefined ? { region } : { region, regionCode };
  }

  /** @internal */
  variant(i: number): Variant {
    this.#variants ??= this.#raw.variants.map(([os, tenancy, license, sw, capacity]) => ({
      operatingSystem: this.str(os),
      tenancy: this.str(tenancy),
      licenseModel: this.str(license),
      preInstalledSw: this.str(sw),
      capacitystatus: this.str(capacity),
    }));
    return this.#variants[i];
  }

  /** @internal */
  term(i: number): ReservedTerm {
    this.#terms ??= this.#raw.reserved_terms.map(([lease, offering, purchase]) => ({
      leaseContractLength: this.str(lease),
      offeringClass: this.str(offering),
      purchaseOption: this.str(purchase),
    }));
    return this.#terms[i];
  }
}

/** One instance type. Each getter decodes on first access and caches the result. */
export class AWSInstance {
  /** The instance type, e.g. `m5.large`. */
  readonly name: string;
  #raw: RawInstance;
  #data: AWSPricingData;
  #attributes?: Readonly<Record<string, string>>;
  #attributesHistory?: readonly AttributeChange[];
  #pricing?: Pricing;
  #pricingHistory?: PricingHistory;

  constructor(name: string, raw: RawInstance, data: AWSPricingData) {
    this.name = name;
    this.#raw = raw;
    this.#data = data;
  }

  /** The publication date of the first price list that listed this instance. */
  get createdAt(): Date {
    return date(this.#raw[5]);
  }

  /** The publication date of the first price list that stopped listing it, or `null` if AWS still lists it. */
  get deletedAt(): Date | null {
    return this.#raw[6] === null ? null : date(this.#raw[6]);
  }

  /** The latest attributes shared by every region. Regional differences are in {@link attributesIn}. */
  get attributes(): Readonly<Record<string, string>> {
    if (!this.#attributes) {
      const out: Record<string, string> = {};
      for (const c of this.attributesHistory) {
        if (c.region !== null) continue;
        if (c.value === null) delete out[c.key];
        else out[c.key] = c.value;
      }
      this.#attributes = out;
    }
    return this.#attributes;
  }

  /**
   * The latest attributes in one AWS location (e.g. `US East (N. Virginia)`): the
   * global ones with that region's overrides on top. A regional override keeps
   * applying even after a newer global change to the same key.
   */
  attributesIn(region: string): Record<string, string> {
    const out = { ...this.attributes };
    const overrides = new Map<string, string | null>();
    for (const c of this.attributesHistory) {
      if (c.region === region) overrides.set(c.key, c.value);
    }
    for (const [k, v] of overrides) {
      if (v === null) delete out[k];
      else out[k] = v;
    }
    return out;
  }

  /** Every attribute change, oldest first, starting with the attributes the instance was first listed with. */
  get attributesHistory(): readonly AttributeChange[] {
    if (!this.#attributesHistory) {
      const d = this.#data;
      const created = this.createdAt;
      const out: AttributeChange[] = this.#raw[0].map(([k, v]) => ({
        at: created,
        key: d.str(k),
        value: d.str(v),
        region: null,
      }));
      const changes = this.#raw[1]
        .map(([ts, key, value, region]) => ({
          at: date(ts!),
          key: d.str(key!),
          value: value === null || value === undefined ? null : d.str(value),
          region: region === null || region === undefined ? null : d.str(region),
        }))
        // Stable, so rows with the same timestamp keep their order (later rows win).
        .sort((a, b) => a.at.getTime() - b.at.getTime());
      this.#attributesHistory = out.concat(changes);
    }
    return this.#attributesHistory;
  }

  /** The current price of everything still offered. */
  get pricing(): Pricing {
    if (!this.#pricing) {
      const { onDemand, reserved } = this.pricingHistory;
      const od = new Map<string, OnDemandPriceChange>();
      for (const r of onDemand) od.set(odKey(r), r);
      const rs = new Map<string, ReservedPriceChange>();
      for (const r of reserved) rs.set(`${odKey(r)}\0${r.leaseContractLength}\0${r.offeringClass}\0${r.purchaseOption}`, r);

      this.#pricing = {
        onDemand: [...od.values()]
          .filter((r) => r.hourly !== null)
          .map(({ at, hourly, ...rest }) => ({ ...rest, hourly: hourly!, since: at })),
        reserved: [...rs.values()]
          .filter((r) => r.hourly !== null)
          .map(({ at, hourly, upfront, ...rest }) => ({ ...rest, hourly: hourly!, upfront: upfront ?? 0, since: at })),
      };
    }
    return this.#pricing;
  }

  /** Every on-demand and reserved price change, oldest first. */
  get pricingHistory(): PricingHistory {
    if (!this.#pricingHistory) {
      const d = this.#data;
      const base = this.#raw[2];
      const byTime = (a: { at: Date }, b: { at: Date }) => a.at.getTime() - b.at.getTime();
      this.#pricingHistory = {
        // [ts, region, variant, price: omitted = base price, null = no longer offered]
        onDemand: this.#raw[3]
          .map(([ts, region, variant, ...price]) => ({
            at: date(ts!),
            ...d.location(region!),
            ...d.variant(variant!),
            hourly: price.length === 0 ? base : price[0],
          }))
          .sort(byTime),
        // [ts, region, variant, term, hourly: null = no longer offered, upfront: omitted if 0]
        reserved: this.#raw[4]
          .map(([ts, region, variant, term, hourly, upfront]) => {
            const removed = hourly === null || hourly === undefined;
            return {
              at: date(ts!),
              ...d.location(region!),
              ...d.variant(variant!),
              ...d.term(term!),
              hourly: removed ? null : hourly,
              upfront: removed ? null : (upfront ?? 0),
            };
          })
          .sort(byTime),
      };
    }
    return this.#pricingHistory;
  }
}

function odKey(r: Location & Variant): string {
  return [r.region, r.operatingSystem, r.tenancy, r.licenseModel, r.preInstalledSw, r.capacitystatus].join("\0");
}
