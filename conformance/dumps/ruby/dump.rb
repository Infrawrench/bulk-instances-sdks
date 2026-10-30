# frozen_string_literal: true

require "json"
require "infrawrench/bulk_instances"

AWSPricingDataError = Infrawrench::BulkInstances::AWSPricingDataError

base_url, cache_path, token, cache, platform = ARGV
ts = ->(t) { t&.to_i }

begin
  options = { base_url:, cache_path:, cache_pricing_data: cache == "1", token: token == "-" ? nil : token }
  data = if platform.nil?
           Infrawrench::BulkInstances.download_aws_ec2_pricing_data(**options)
         else
           Infrawrench::BulkInstances.download_aws_pricing_data(platform, **options)
         end
rescue AWSPricingDataError => e
  puts JSON.generate({ error: { status: e.status, message: e.message } })
  exit 3
end

# Data#to_h, with camelCase keys and Unix-second times.
camel = ->(h) { h.to_h { |k, v| [k.to_s.gsub(/_(\w)/) { Regexp.last_match(1).upcase }, v.is_a?(Time) ? v.to_i : v] } }

regions = data.regions
locations = regions.keys + %w[Mystery Nowhere]
out = {
  offer: data.offer,
  variantKeys: data.variant_keys,
  snapshots: data.snapshots.map(&ts),
  regions:,
  keys: data.keys.sort,
  has: { "m5.large" => data.has?("m5.large"), "nope" => data.key?("nope") },
  getMissing: data["nope"],
  instances: data.keys.to_h do |k|
    i = data.get(k)
    p = i.pricing
    h = i.pricing_history
    [k, {
      name: i.name, createdAt: ts.(i.created_at), deletedAt: ts.(i.deleted_at),
      attributes: i.attributes,
      attributesIn: locations.to_h { |r| [r, i.attributes_in(r)] },
      attributesHistory: i.attributes_history.map { |c| camel.(c.to_h) },
      pricing: { onDemand: p.on_demand.map { |r| camel.(r.to_h) }, reserved: p.reserved.map { |r| camel.(r.to_h) } },
      pricingHistory: { onDemand: h.on_demand.map { |r| camel.(r.to_h) }, reserved: h.reserved.map { |r| camel.(r.to_h) } },
    }]
  end,
}
puts JSON.pretty_generate(out)
