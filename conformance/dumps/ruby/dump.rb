# frozen_string_literal: true

require "json"
require "infrawrench/bulk_instances"

BI = Infrawrench::BulkInstances
AWSPricingDataError = BI::AWSPricingDataError

base_url, cache_path, token, cache, platform, instance_type = ARGV
ts = ->(t) { t&.to_i }
token = nil if token == "-"

# Data#to_h, with camelCase keys and Unix-second times.
camel = ->(h) { h.to_h { |k, v| [k.to_s.gsub(/_(\w)/) { Regexp.last_match(1).upcase }, v.is_a?(Time) ? v.to_i : v] } }

dump_instance = lambda do |i, region_names|
  p = i.pricing
  h = i.pricing_history
  {
    name: i.name, createdAt: ts.(i.created_at), deletedAt: ts.(i.deleted_at),
    attributes: i.attributes,
    attributesIn: (region_names + %w[Mystery Nowhere]).to_h { |r| [r, i.attributes_in(r)] },
    attributesHistory: i.attributes_history.map { |c| camel.(c.to_h) },
    pricing: { onDemand: p.on_demand.map { |r| camel.(r.to_h) }, reserved: p.reserved.map { |r| camel.(r.to_h) } },
    pricingHistory: { onDemand: h.on_demand.map { |r| camel.(r.to_h) }, reserved: h.reserved.map { |r| camel.(r.to_h) } },
  }
end

unless instance_type.nil?
  begin
    i = BI.fetch_aws_instance(platform, instance_type, token:, base_url:)
  rescue AWSPricingDataError => e
    puts JSON.generate({ error: { status: e.status, message: e.message } })
    exit 3
  end
  # The regions its attributes are overridden in; every other one is the same as `attributes`.
  region_names = i.nil? ? [] : i.attributes_history.filter_map(&:region).uniq.sort
  puts JSON.pretty_generate({ instance: i && dump_instance.(i, region_names) })
  exit 0
end

# A provider function's failure must be that provider's error.
def expect_error(provider_error)
  yield
rescue AWSPricingDataError => e
  unless e.is_a?(provider_error)
    warn "expected a #{provider_error}, got #{e.class}"
    exit 1
  end
  raise
end

def expect_types(data, data_class, instance_class)
  first = data.keys.first
  return data if data.is_a?(data_class) && (first.nil? || [data.get(first), data[first]].all?(instance_class))

  warn "expected #{data_class} and #{instance_class}"
  exit 1
end

begin
  options = { base_url:, cache_path:, cache_pricing_data: cache == "1", token: }
  # RunPod and Alibaba have their own functions and classes, and their own errors.
  data = case platform
         when nil then BI.download_aws_ec2_pricing_data(**options)
         when "runpod"
           expect_types(expect_error(BI::RunpodPricingDataError) { BI.download_runpod_pricing_data(**options) },
                        BI::RunpodPricingData, BI::RunpodInstance)
         when "alibaba"
           expect_types(expect_error(BI::AlibabaPricingDataError) { BI.download_alibaba_pricing_data(**options) },
                        BI::AlibabaPricingData, BI::AlibabaInstance)
         else BI.download_aws_pricing_data(platform, **options)
         end
rescue AWSPricingDataError => e
  puts JSON.generate({ error: { status: e.status, message: e.message } })
  exit 3
end

regions = data.regions
out = {
  offer: data.offer,
  variantKeys: data.variant_keys,
  snapshots: data.snapshots.map(&ts),
  regions:,
  keys: data.keys.sort,
  has: { "m5.large" => data.has?("m5.large"), "nope" => data.key?("nope") },
  getMissing: data["nope"],
  instances: data.keys.to_h { |k| [k, dump_instance.(data.get(k), regions.keys)] },
}
puts JSON.pretty_generate(out)
