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

def expect_instance(instance, instance_class)
  return instance if instance.nil? || instance.is_a?(instance_class)

  warn "expected #{instance_class}"
  exit 1
end

unless instance_type.nil?
  begin
    # RunPod and Alibaba have their own functions, returning their own classes and errors.
    i = case platform
        when "runpod"
          expect_instance(expect_error(BI::RunpodPricingDataError) { BI.fetch_runpod_instance(instance_type, token:, base_url:) },
                          BI::RunpodInstance)
        when "alibaba"
          expect_instance(expect_error(BI::AlibabaPricingDataError) { BI.fetch_alibaba_instance(instance_type, token:, base_url:) },
                          BI::AlibabaInstance)
        else BI.fetch_aws_instance(platform, instance_type, token:, base_url:)
        end
  rescue AWSPricingDataError => e
    puts JSON.generate({ error: { status: e.status, message: e.message } })
    exit 3
  end
  # The regions its attributes are overridden in; every other one is the same as `attributes`.
  region_names = i.nil? ? [] : i.attributes_history.filter_map(&:region).uniq.sort
  puts JSON.pretty_generate({ instance: i && dump_instance.(i, region_names) })
  exit 0
end

begin
  options = { base_url:, cache_path:, cache_pricing_data: cache == "1", token: }
  # Clouds other than AWS have their own functions and classes, and their own errors.
  data = case platform
         when nil then BI.download_aws_ec2_pricing_data(**options)
         when "runpod"
           expect_types(expect_error(BI::RunpodPricingDataError) { BI.download_runpod_pricing_data(**options) },
                        BI::RunpodPricingData, BI::RunpodInstance)
         when "alibaba"
           expect_types(expect_error(BI::AlibabaPricingDataError) { BI.download_alibaba_pricing_data(**options) },
                        BI::AlibabaPricingData, BI::AlibabaInstance)
         when "azure"
           expect_types(expect_error(BI::AzurePricingDataError) { BI.download_azure_pricing_data(**options) },
                        BI::AzurePricingData, BI::AzureInstance)
         when "gcp"
           expect_types(expect_error(BI::GCPPricingDataError) { BI.download_gcp_pricing_data(**options) },
                        BI::GCPPricingData, BI::GCPInstance)
         when "hetzner"
           expect_types(expect_error(BI::HetznerPricingDataError) { BI.download_hetzner_pricing_data(**options) },
                        BI::HetznerPricingData, BI::HetznerInstance)
         when "hetznerauction"
           expect_types(expect_error(BI::HetznerAuctionPricingDataError) { BI.download_hetzner_auction_pricing_data(**options) },
                        BI::HetznerAuctionPricingData, BI::HetznerAuctionInstance)
         when "ovh"
           expect_types(expect_error(BI::OVHPricingDataError) { BI.download_ovh_pricing_data(**options) },
                        BI::OVHPricingData, BI::OVHInstance)
         when "ovheco"
           expect_types(expect_error(BI::OVHEcoPricingDataError) { BI.download_ovh_eco_pricing_data(**options) },
                        BI::OVHEcoPricingData, BI::OVHEcoInstance)
         when "oracle"
           expect_types(expect_error(BI::OraclePricingDataError) { BI.download_oracle_pricing_data(**options) },
                        BI::OraclePricingData, BI::OracleInstance)
         when "ibm"
           expect_types(expect_error(BI::IBMPricingDataError) { BI.download_ibm_pricing_data(**options) },
                        BI::IBMPricingData, BI::IBMInstance)
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
