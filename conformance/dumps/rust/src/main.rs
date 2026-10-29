use std::time::{SystemTime, UNIX_EPOCH};

use infrawrench_bulk_instances::{Options, ReservedTerm, Variant, download_aws_ec2_pricing_data};
use serde_json::{Map, Value, json};

fn ts(t: SystemTime) -> Value {
    json!(t.duration_since(UNIX_EPOCH).unwrap().as_secs())
}

fn base(region: &str, region_code: &Option<String>, v: &Variant) -> Map<String, Value> {
    let Value::Object(m) = json!({
        "region": region, "regionCode": region_code,
        "operatingSystem": v.operating_system, "tenancy": v.tenancy, "licenseModel": v.license_model,
        "preInstalledSw": v.pre_installed_sw, "capacitystatus": v.capacitystatus,
    }) else {
        unreachable!()
    };
    m
}

fn with_term(mut m: Map<String, Value>, t: &ReservedTerm) -> Map<String, Value> {
    m.insert("leaseContractLength".into(), json!(t.lease_contract_length));
    m.insert("offeringClass".into(), json!(t.offering_class));
    m.insert("purchaseOption".into(), json!(t.purchase_option));
    m
}

fn extend(mut m: Map<String, Value>, extra: Value) -> Value {
    if let Value::Object(e) = extra {
        m.extend(e)
    }
    Value::Object(m)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let [base_url, cache_path, token, cache] = &args[..] else {
        panic!("usage: dump <baseUrl> <cacheDir> <token|-> <1|0>")
    };
    let options = Options {
        token: (token != "-").then(|| token.clone()),
        cache_pricing_data: cache == "1",
        cache_path: Some(cache_path.into()),
        base_url: Some(base_url.clone()),
    };
    let data = match download_aws_ec2_pricing_data(&options) {
        Ok(d) => d,
        Err(e) => {
            println!(
                "{}",
                json!({ "error": { "status": e.status(), "message": e.to_string() } })
            );
            std::process::exit(3);
        }
    };

    let regions = data.regions();
    let mut keys: Vec<&str> = data.keys().collect();
    keys.sort();
    let mut instances = Map::new();
    for k in data.keys() {
        let i = data.get(k).unwrap();
        let (p, h) = (i.pricing(), i.pricing_history());
        let mut attributes_in = Map::new();
        for r in regions
            .keys()
            .map(String::as_str)
            .chain(["Mystery", "Nowhere"])
        {
            attributes_in.insert(r.into(), json!(i.attributes_in(r)));
        }
        let history: Vec<Value> = i
            .attributes_history()
            .iter()
            .map(|c| json!({ "at": ts(c.at), "key": c.key, "value": c.value, "region": c.region }))
            .collect();
        let on_demand: Vec<Value> = p
            .on_demand
            .iter()
            .map(|r| {
                extend(
                    base(&r.region, &r.region_code, &r.variant),
                    json!({ "hourly": r.hourly, "since": ts(r.since) }),
                )
            })
            .collect();
        let reserved: Vec<Value> = p
            .reserved
            .iter()
            .map(|r| {
                extend(
                    with_term(base(&r.region, &r.region_code, &r.variant), &r.term),
                    json!({ "hourly": r.hourly, "upfront": r.upfront, "since": ts(r.since) }),
                )
            })
            .collect();
        let od_history: Vec<Value> = h
            .on_demand
            .iter()
            .map(|r| {
                extend(
                    base(&r.region, &r.region_code, &r.variant),
                    json!({ "at": ts(r.at), "hourly": r.hourly }),
                )
            })
            .collect();
        let rs_history: Vec<Value> = h
            .reserved
            .iter()
            .map(|r| {
                extend(
                    with_term(base(&r.region, &r.region_code, &r.variant), &r.term),
                    json!({ "at": ts(r.at), "hourly": r.hourly, "upfront": r.upfront }),
                )
            })
            .collect();
        instances.insert(k.into(), json!({
            "name": i.name(), "createdAt": ts(i.created_at()), "deletedAt": i.deleted_at().map(ts),
            "attributes": i.attributes(),
            "attributesIn": attributes_in,
            "attributesHistory": history,
            "pricing": { "onDemand": on_demand, "reserved": reserved },
            "pricingHistory": { "onDemand": od_history, "reserved": rs_history },
        }));
    }
    let out = json!({
        "snapshots": data.snapshots().into_iter().map(ts).collect::<Vec<_>>(),
        "regions": regions,
        "keys": keys,
        "has": { "m5.large": data.has("m5.large"), "nope": data.has("nope") },
        "getMissing": data.get("nope").map(|i| i.name()),
        "instances": instances,
    });
    println!("{}", serde_json::to_string_pretty(&out).unwrap());
}
