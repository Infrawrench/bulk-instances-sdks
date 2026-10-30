use std::collections::BTreeSet;
use std::time::{SystemTime, UNIX_EPOCH};

use infrawrench_bulk_instances::{
    AwsInstance, AwsInstanceOptions, Error, Options, ReservedTerm, Variant,
    download_aws_ec2_pricing_data, download_aws_pricing_data, fetch_aws_instance,
};
use serde_json::{Map, Value, json};

fn ts(t: SystemTime) -> Value {
    json!(t.duration_since(UNIX_EPOCH).unwrap().as_secs())
}

fn base(region: &str, region_code: &Option<String>, v: &Variant) -> Map<String, Value> {
    let Value::Object(m) = json!({
        "region": region, "regionCode": region_code,
        "variant": v.fields.iter().map(|(k, v)| (k.clone(), json!(v))).collect::<Map<_, _>>(),
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

fn error(e: Error) -> ! {
    println!(
        "{}",
        json!({ "error": { "status": e.status(), "message": e.to_string() } })
    );
    std::process::exit(3);
}

fn dump_instance<'a>(i: &AwsInstance, region_names: impl Iterator<Item = &'a str>) -> Value {
    let (p, h) = (i.pricing(), i.pricing_history());
    let mut attributes_in = Map::new();
    for r in region_names.chain(["Mystery", "Nowhere"]) {
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
    json!({
        "name": i.name(), "createdAt": ts(i.created_at()), "deletedAt": i.deleted_at().map(ts),
        "attributes": i.attributes(),
        "attributesIn": attributes_in,
        "attributesHistory": history,
        "pricing": { "onDemand": on_demand, "reserved": reserved },
        "pricingHistory": { "onDemand": od_history, "reserved": rs_history },
    })
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let (base_url, cache_path, token, cache, platform, instance) = match &args[..] {
        [b, p, t, c] => (b, p, t, c, None, None),
        [b, p, t, c, platform] => (b, p, t, c, Some(platform), None),
        [b, p, t, c, platform, instance] => (b, p, t, c, Some(platform), Some(instance)),
        _ => panic!("usage: dump <baseUrl> <cacheDir> <token|-> <1|0> [platform [instance]]"),
    };
    let token = (token != "-").then(|| token.clone());

    if let (Some(platform), Some(instance)) = (platform, instance) {
        let options = AwsInstanceOptions {
            token,
            base_url: Some(base_url.clone()),
        };
        let i = fetch_aws_instance(platform, instance, &options).unwrap_or_else(|e| error(e));
        let dumped = i.map(|i| {
            // The regions its attributes are overridden in; every other one is the same as `attributes`.
            let regions: BTreeSet<&str> = i
                .attributes_history()
                .iter()
                .filter_map(|c| c.region.as_deref())
                .collect();
            dump_instance(&i, regions.into_iter())
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&json!({ "instance": dumped })).unwrap()
        );
        return;
    }

    let options = Options {
        token,
        cache_pricing_data: cache == "1",
        cache_path: Some(cache_path.into()),
        base_url: Some(base_url.clone()),
    };
    let result = match platform {
        None => download_aws_ec2_pricing_data(&options),
        Some(platform) => download_aws_pricing_data(platform, &options),
    };
    let data = result.unwrap_or_else(|e| error(e));

    let regions = data.regions();
    let mut keys: Vec<&str> = data.keys().collect();
    keys.sort();
    let mut instances = Map::new();
    for k in data.keys() {
        let i = data.get(k).unwrap();
        instances.insert(
            k.into(),
            dump_instance(i, regions.keys().map(String::as_str)),
        );
    }
    let out = json!({
        "offer": data.offer(),
        "variantKeys": data.variant_keys(),
        "snapshots": data.snapshots().into_iter().map(ts).collect::<Vec<_>>(),
        "regions": regions,
        "keys": keys,
        "has": { "m5.large": data.has("m5.large"), "nope": data.has("nope") },
        "getMissing": data.get("nope").map(|i| i.name()),
        "instances": instances,
    });
    println!("{}", serde_json::to_string_pretty(&out).unwrap());
}
