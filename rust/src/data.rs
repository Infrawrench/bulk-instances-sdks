use std::collections::hash_map::Entry;
use std::collections::{BTreeMap, HashMap};
use std::fmt;
use std::hash::Hash;
use std::sync::{Arc, OnceLock};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use crate::raw::{BundleFile, RawInstance};

/// Attributes of each AWS location (`regionCode`, `locationType`), keyed by location name.
pub type Regions = BTreeMap<String, BTreeMap<String, String>>;

/// The product fields that pick a price.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
#[non_exhaustive]
pub struct Variant {
    pub operating_system: String,
    pub tenancy: String,
    pub license_model: String,
    pub pre_installed_sw: String,
    pub capacitystatus: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
#[non_exhaustive]
pub struct ReservedTerm {
    pub lease_contract_length: String,
    pub offering_class: String,
    pub purchase_option: String,
}

#[derive(Debug, Clone, PartialEq)]
#[non_exhaustive]
pub struct OnDemandPrice {
    /// The AWS location name, e.g. `US East (N. Virginia)`.
    pub region: String,
    /// e.g. `us-east-1`. `None` for locations the price list never gave a code.
    pub region_code: Option<String>,
    pub variant: Variant,
    /// USD per hour.
    pub hourly: f64,
    /// When this price took effect.
    pub since: SystemTime,
}

#[derive(Debug, Clone, PartialEq)]
#[non_exhaustive]
pub struct ReservedPrice {
    /// The AWS location name, e.g. `US East (N. Virginia)`.
    pub region: String,
    /// e.g. `us-east-1`. `None` for locations the price list never gave a code.
    pub region_code: Option<String>,
    pub variant: Variant,
    pub term: ReservedTerm,
    /// USD per hour.
    pub hourly: f64,
    /// USD paid up front.
    pub upfront: f64,
    pub since: SystemTime,
}

#[derive(Debug, Clone, PartialEq)]
#[non_exhaustive]
pub struct Pricing {
    pub on_demand: Vec<OnDemandPrice>,
    pub reserved: Vec<ReservedPrice>,
}

#[derive(Debug, Clone, PartialEq)]
#[non_exhaustive]
pub struct OnDemandPriceChange {
    /// The AWS location name, e.g. `US East (N. Virginia)`.
    pub region: String,
    /// e.g. `us-east-1`. `None` for locations the price list never gave a code.
    pub region_code: Option<String>,
    pub variant: Variant,
    pub at: SystemTime,
    /// `None` means no longer offered from `at` on.
    pub hourly: Option<f64>,
}

#[derive(Debug, Clone, PartialEq)]
#[non_exhaustive]
pub struct ReservedPriceChange {
    /// The AWS location name, e.g. `US East (N. Virginia)`.
    pub region: String,
    /// e.g. `us-east-1`. `None` for locations the price list never gave a code.
    pub region_code: Option<String>,
    pub variant: Variant,
    pub term: ReservedTerm,
    pub at: SystemTime,
    /// `None` means no longer offered from `at` on.
    pub hourly: Option<f64>,
    pub upfront: Option<f64>,
}

#[derive(Debug, Clone, PartialEq)]
#[non_exhaustive]
pub struct PricingHistory {
    /// Oldest first.
    pub on_demand: Vec<OnDemandPriceChange>,
    /// Oldest first.
    pub reserved: Vec<ReservedPriceChange>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub struct AttributeChange {
    pub at: SystemTime,
    pub key: String,
    /// `None` means the attribute was removed.
    pub value: Option<String>,
    /// The AWS location this change applies to, or `None` for every region.
    pub region: Option<String>,
}

fn date(ts: f64) -> SystemTime {
    if ts >= 0.0 {
        UNIX_EPOCH + Duration::from_secs_f64(ts)
    } else {
        UNIX_EPOCH - Duration::from_secs_f64(-ts)
    }
}

/// The parsed bundle and the parts every instance shares, each decoded once on first use.
struct Shared {
    raw: BundleFile,
    regions: OnceLock<Regions>,
    variants: OnceLock<Vec<Variant>>,
    terms: OnceLock<Vec<ReservedTerm>>,
}

impl Shared {
    fn str(&self, i: u32) -> &str {
        match self.raw.compression_table.get(i as usize) {
            Some(s) => s,
            None => panic!("string index {i} out of range"),
        }
    }

    fn regions(&self) -> &Regions {
        self.regions.get_or_init(|| {
            self.raw
                .regions
                .iter()
                .map(|(loc, pairs)| {
                    let attrs = pairs
                        .iter()
                        .map(|&[k, v]| (self.str(k).to_owned(), self.str(v).to_owned()));
                    (self.str(*loc).to_owned(), attrs.collect())
                })
                .collect()
        })
    }

    /// The location name and its `regionCode`, if it has one.
    fn location(&self, i: u32) -> (String, Option<String>) {
        let region = self.str(i);
        let region_code = self
            .regions()
            .get(region)
            .and_then(|attrs| attrs.get("regionCode"))
            .cloned();
        (region.to_owned(), region_code)
    }

    fn variant(&self, i: u32) -> &Variant {
        let variants = self.variants.get_or_init(|| {
            self.raw
                .variants
                .iter()
                .map(|&[os, tenancy, license, sw, capacity]| Variant {
                    operating_system: self.str(os).to_owned(),
                    tenancy: self.str(tenancy).to_owned(),
                    license_model: self.str(license).to_owned(),
                    pre_installed_sw: self.str(sw).to_owned(),
                    capacitystatus: self.str(capacity).to_owned(),
                })
                .collect()
        });
        match variants.get(i as usize) {
            Some(v) => v,
            None => panic!("variant index {i} out of range"),
        }
    }

    fn term(&self, i: u32) -> &ReservedTerm {
        let terms = self.terms.get_or_init(|| {
            self.raw
                .reserved_terms
                .iter()
                .map(|&[lease, offering, purchase]| ReservedTerm {
                    lease_contract_length: self.str(lease).to_owned(),
                    offering_class: self.str(offering).to_owned(),
                    purchase_option: self.str(purchase).to_owned(),
                })
                .collect()
        });
        match terms.get(i as usize) {
            Some(t) => t,
            None => panic!("reserved term index {i} out of range"),
        }
    }
}

/// The AWS EC2 pricing data, keyed by instance type.
///
/// Nothing is decoded until it is asked for: [`get`](Self::get) wraps the raw rows, and each
/// getter on the returned [`AwsInstance`] decodes its part on first access and keeps the result.
///
/// `AwsPricingData` is `Send + Sync`: it can be shared between threads (e.g. in an `Arc`), and
/// each part is decoded once, by whichever thread asks for it first.
///
/// # Panics
///
/// The getters panic if the bundle refers to a string, variant or term it does not contain.
pub struct AwsPricingData {
    shared: Arc<Shared>,
    instances: Box<[OnceLock<AwsInstance>]>,
}

impl AwsPricingData {
    pub(crate) fn new(raw: BundleFile) -> Self {
        let instances = raw.instances.rows.iter().map(|_| OnceLock::new()).collect();
        let shared = Arc::new(Shared {
            raw,
            regions: OnceLock::new(),
            variants: OnceLock::new(),
            terms: OnceLock::new(),
        });
        Self { shared, instances }
    }

    /// Every instance type in the bundle, including ones AWS no longer lists (see
    /// [`AwsInstance::deleted_at`]).
    pub fn keys(&self) -> impl ExactSizeIterator<Item = &str> {
        self.shared
            .raw
            .instances
            .rows
            .iter()
            .map(|(name, _)| name.as_str())
    }

    pub fn has(&self, instance_type: &str) -> bool {
        self.shared.raw.instances.index.contains_key(instance_type)
    }

    /// The instance with this type (e.g. `m5.large`), or `None` if the bundle has never listed it.
    pub fn get(&self, instance_type: &str) -> Option<&AwsInstance> {
        let &index = self.shared.raw.instances.index.get(instance_type)?;
        Some(
            self.instances[index].get_or_init(|| AwsInstance::new(Arc::clone(&self.shared), index)),
        )
    }

    /// The publication date of every AWS price list in the bundle, oldest first.
    pub fn snapshots(&self) -> Vec<SystemTime> {
        self.shared
            .raw
            .snapshots
            .iter()
            .copied()
            .map(date)
            .collect()
    }

    /// Attributes of each AWS location (`regionCode`, `locationType`), keyed by location name.
    pub fn regions(&self) -> &Regions {
        self.shared.regions()
    }
}

impl fmt::Debug for AwsPricingData {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("AwsPricingData")
            .field("instances", &self.instances.len())
            .finish_non_exhaustive()
    }
}

/// One instance type. Each getter decodes on first access and caches the result.
pub struct AwsInstance {
    shared: Arc<Shared>,
    index: usize,
    attributes: OnceLock<BTreeMap<String, String>>,
    attributes_history: OnceLock<Vec<AttributeChange>>,
    pricing: OnceLock<Pricing>,
    pricing_history: OnceLock<PricingHistory>,
}

impl AwsInstance {
    fn new(shared: Arc<Shared>, index: usize) -> Self {
        Self {
            shared,
            index,
            attributes: OnceLock::new(),
            attributes_history: OnceLock::new(),
            pricing: OnceLock::new(),
            pricing_history: OnceLock::new(),
        }
    }

    fn raw(&self) -> &RawInstance {
        &self.shared.raw.instances.rows[self.index].1
    }

    /// The instance type, e.g. `m5.large`.
    pub fn name(&self) -> &str {
        &self.shared.raw.instances.rows[self.index].0
    }

    /// The publication date of the first price list that listed this instance.
    pub fn created_at(&self) -> SystemTime {
        date(self.raw().created_at)
    }

    /// The publication date of the first price list that stopped listing it, or `None` if AWS
    /// still lists it.
    pub fn deleted_at(&self) -> Option<SystemTime> {
        self.raw().deleted_at.map(date)
    }

    /// The latest attributes shared by every region. Regional differences are in
    /// [`attributes_in`](Self::attributes_in).
    pub fn attributes(&self) -> &BTreeMap<String, String> {
        self.attributes.get_or_init(|| {
            let mut out = BTreeMap::new();
            for c in self
                .attributes_history()
                .iter()
                .filter(|c| c.region.is_none())
            {
                match &c.value {
                    Some(v) => out.insert(c.key.clone(), v.clone()),
                    None => out.remove(&c.key),
                };
            }
            out
        })
    }

    /// The latest attributes in one AWS location (e.g. `US East (N. Virginia)`): the
    /// global ones with that region's overrides on top. A regional override keeps
    /// applying even after a newer global change to the same key.
    pub fn attributes_in(&self, region: &str) -> BTreeMap<String, String> {
        let mut out = self.attributes().clone();
        for c in self
            .attributes_history()
            .iter()
            .filter(|c| c.region.as_deref() == Some(region))
        {
            match &c.value {
                Some(v) => out.insert(c.key.clone(), v.clone()),
                None => out.remove(&c.key),
            };
        }
        out
    }

    /// Every attribute change, oldest first, starting with the attributes the instance was
    /// first listed with.
    pub fn attributes_history(&self) -> &[AttributeChange] {
        self.attributes_history.get_or_init(|| {
            let d = &*self.shared;
            let raw = self.raw();
            let created = self.created_at();
            let mut out: Vec<AttributeChange> = raw
                .attrs
                .iter()
                .map(|&[k, v]| AttributeChange {
                    at: created,
                    key: d.str(k).to_owned(),
                    value: Some(d.str(v).to_owned()),
                    region: None,
                })
                .collect();
            let mut changes: Vec<AttributeChange> = raw
                .attr_changes
                .iter()
                .map(|c| AttributeChange {
                    at: date(c.at),
                    key: d.str(c.key).to_owned(),
                    value: c.value.map(|v| d.str(v).to_owned()),
                    region: c.region.map(|r| d.str(r).to_owned()),
                })
                .collect();
            // Stable, so rows with the same timestamp keep their order (later rows win).
            changes.sort_by_key(|c| c.at);
            out.append(&mut changes);
            out
        })
    }

    /// The current price of everything still offered.
    pub fn pricing(&self) -> &Pricing {
        self.pricing.get_or_init(|| {
            let history = self.pricing_history();
            let on_demand = latest(&history.on_demand, |r| (&r.region, &r.variant))
                .into_iter()
                .filter_map(|r| {
                    Some(OnDemandPrice {
                        region: r.region.clone(),
                        region_code: r.region_code.clone(),
                        variant: r.variant.clone(),
                        hourly: r.hourly?,
                        since: r.at,
                    })
                })
                .collect();
            let reserved = latest(&history.reserved, |r| (&r.region, &r.variant, &r.term))
                .into_iter()
                .filter_map(|r| {
                    Some(ReservedPrice {
                        region: r.region.clone(),
                        region_code: r.region_code.clone(),
                        variant: r.variant.clone(),
                        term: r.term.clone(),
                        hourly: r.hourly?,
                        upfront: r.upfront.unwrap_or(0.0),
                        since: r.at,
                    })
                })
                .collect();
            Pricing {
                on_demand,
                reserved,
            }
        })
    }

    /// Every on-demand and reserved price change, oldest first.
    pub fn pricing_history(&self) -> &PricingHistory {
        self.pricing_history.get_or_init(|| {
            let d = &*self.shared;
            let raw = self.raw();
            let mut on_demand: Vec<OnDemandPriceChange> = raw
                .on_demand
                .iter()
                .map(|r| {
                    let (region, region_code) = d.location(r.region);
                    OnDemandPriceChange {
                        region,
                        region_code,
                        variant: d.variant(r.variant).clone(),
                        at: date(r.at),
                        hourly: r.price.unwrap_or(Some(raw.base_price)),
                    }
                })
                .collect();
            on_demand.sort_by_key(|r| r.at);
            let mut reserved: Vec<ReservedPriceChange> = raw
                .reserved
                .iter()
                .map(|r| {
                    let (region, region_code) = d.location(r.region);
                    ReservedPriceChange {
                        region,
                        region_code,
                        variant: d.variant(r.variant).clone(),
                        term: d.term(r.term).clone(),
                        at: date(r.at),
                        hourly: r.hourly,
                        upfront: r.hourly.map(|_| r.upfront.unwrap_or(0.0)),
                    }
                })
                .collect();
            reserved.sort_by_key(|r| r.at);
            PricingHistory {
                on_demand,
                reserved,
            }
        })
    }
}

impl fmt::Debug for AwsInstance {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("AwsInstance")
            .field("name", &self.name())
            .finish_non_exhaustive()
    }
}

/// The last change per key, keyed in order of first appearance.
fn latest<'a, T, K: Hash + Eq>(changes: &'a [T], key: impl Fn(&'a T) -> K) -> Vec<&'a T> {
    let mut out: Vec<&T> = Vec::new();
    let mut index = HashMap::new();
    for c in changes {
        match index.entry(key(c)) {
            Entry::Occupied(e) => out[*e.get()] = c,
            Entry::Vacant(e) => {
                e.insert(out.len());
                out.push(c);
            }
        }
    }
    out
}

const _: () = {
    const fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<AwsPricingData>();
    assert_send_sync::<AwsInstance>();
};
