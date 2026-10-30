//! The bundle as instances-bundler writes it; every string is an index into `compression_table`.

use std::collections::HashMap;
use std::collections::hash_map::Entry;
use std::fmt;

use serde::Deserialize;
use serde::de::{Deserializer, MapAccess, Visitor};

#[derive(Deserialize)]
pub(crate) struct BundleFile {
    /// The AWS offer code. EC2 bundles leave it out.
    #[serde(default)]
    pub offer: Option<String>,
    pub compression_table: Vec<String>,
    pub snapshots: Vec<f64>,
    pub regions: Vec<(u32, Vec<[u32; 2]>)>,
    /// The names of each variant's fields. EC2 bundles leave it out (see `EC2_VARIANT_KEYS`).
    #[serde(default)]
    pub variant_keys: Option<Vec<String>>,
    pub variants: Vec<Vec<u32>>,
    pub reserved_terms: Vec<[u32; 3]>,
    pub instances: Instances,
}

/// The instances in bundle order; a repeated key keeps its first position and its last value.
pub(crate) struct Instances {
    pub rows: Vec<(String, RawInstance)>,
    pub index: HashMap<String, usize>,
}

#[derive(Deserialize)]
pub(crate) struct RawInstance {
    pub attrs: Vec<[u32; 2]>,
    pub attr_changes: Vec<AttrChangeRow>,
    pub base_price: f64,
    pub on_demand: Vec<OnDemandRow>,
    pub reserved: Vec<ReservedRow>,
    pub created_at: f64,
    pub deleted_at: Option<f64>,
}

/// `[ts, key, value?, region?]`: value missing or null = removed, region missing or null = global.
#[derive(Deserialize)]
pub(crate) struct AttrChangeRow {
    pub at: f64,
    pub key: u32,
    #[serde(default)]
    pub value: Option<u32>,
    #[serde(default)]
    pub region: Option<u32>,
}

/// `[ts, region, variant, price?]`: price omitted = base price, null = no longer offered.
#[derive(Deserialize)]
pub(crate) struct OnDemandRow {
    pub at: f64,
    pub region: u32,
    pub variant: u32,
    #[serde(default, deserialize_with = "present")]
    pub price: Option<Option<f64>>,
}

/// `[ts, region, variant, term, hourly?, upfront?]`: hourly null = no longer offered, upfront omitted if 0.
#[derive(Deserialize)]
pub(crate) struct ReservedRow {
    pub at: f64,
    pub region: u32,
    pub variant: u32,
    pub term: u32,
    #[serde(default)]
    pub hourly: Option<f64>,
    #[serde(default)]
    pub upfront: Option<f64>,
}

/// Tells a present `null` (`Some(None)`) from a missing element (`None`, via `#[serde(default)]`).
fn present<'de, D: Deserializer<'de>>(d: D) -> Result<Option<Option<f64>>, D::Error> {
    Option::<f64>::deserialize(d).map(Some)
}

impl<'de> Deserialize<'de> for Instances {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        struct InstancesVisitor;

        impl<'de> Visitor<'de> for InstancesVisitor {
            type Value = Instances;

            fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str("a map of instance types to instance rows")
            }

            fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Instances, A::Error> {
                let mut rows: Vec<(String, RawInstance)> =
                    Vec::with_capacity(map.size_hint().unwrap_or(0));
                let mut index: HashMap<String, usize> = HashMap::with_capacity(rows.capacity());
                while let Some((name, raw)) = map.next_entry::<String, RawInstance>()? {
                    match index.entry(name) {
                        Entry::Occupied(e) => rows[*e.get()].1 = raw,
                        Entry::Vacant(e) => {
                            rows.push((e.key().clone(), raw));
                            e.insert(rows.len() - 1);
                        }
                    }
                }
                Ok(Instances { rows, index })
            }
        }

        d.deserialize_map(InstancesVisitor)
    }
}
