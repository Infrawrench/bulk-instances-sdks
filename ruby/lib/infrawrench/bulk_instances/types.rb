# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # Every price and price change starts with its location and variant:
    #
    # - +region+: the AWS location name, e.g. <tt>US East (N. Virginia)</tt>.
    # - +region_code+: e.g. +us-east-1+. +nil+ for locations the price list never gave a code.
    # - +variant+: every field that picks the price, as a frozen <tt>Hash{String => String}</tt> keyed
    #   by name in AWSPricingData#variant_keys order: for RDS, +databaseEngine+, +deploymentOption+ and so on.
    # - +operating_system+, +tenancy+, +license_model+, +pre_installed_sw+, +capacitystatus+: EC2's
    #   variant fields. For other platforms these are <tt>""</tt> unless the platform shares the field.

    # The product fields that pick a price.
    Variant = Data.define(:variant, :operating_system, :tenancy, :license_model, :pre_installed_sw, :capacitystatus)

    ReservedTerm = Data.define(:lease_contract_length, :offering_class, :purchase_option)

    # @!attribute [r] hourly
    #   @return [Float] USD per hour.
    # @!attribute [r] since
    #   @return [Time] When this price took effect.
    OnDemandPrice = Data.define(
      :region, :region_code,
      :variant, :operating_system, :tenancy, :license_model, :pre_installed_sw, :capacitystatus,
      :hourly, :since,
    )

    # @!attribute [r] hourly
    #   @return [Float] USD per hour.
    # @!attribute [r] upfront
    #   @return [Float] USD paid up front.
    # @!attribute [r] since
    #   @return [Time]
    ReservedPrice = Data.define(
      :region, :region_code,
      :variant, :operating_system, :tenancy, :license_model, :pre_installed_sw, :capacitystatus,
      :lease_contract_length, :offering_class, :purchase_option,
      :hourly, :upfront, :since,
    )

    # @!attribute [r] on_demand
    #   @return [Array<OnDemandPrice>]
    # @!attribute [r] reserved
    #   @return [Array<ReservedPrice>]
    Pricing = Data.define(:on_demand, :reserved)

    # @!attribute [r] at
    #   @return [Time]
    # @!attribute [r] hourly
    #   @return [Float, nil] +nil+ means no longer offered from +at+ on.
    OnDemandPriceChange = Data.define(
      :at, :region, :region_code,
      :variant, :operating_system, :tenancy, :license_model, :pre_installed_sw, :capacitystatus,
      :hourly,
    )

    # @!attribute [r] at
    #   @return [Time]
    # @!attribute [r] hourly
    #   @return [Float, nil] +nil+ means no longer offered from +at+ on.
    # @!attribute [r] upfront
    #   @return [Float, nil]
    ReservedPriceChange = Data.define(
      :at, :region, :region_code,
      :variant, :operating_system, :tenancy, :license_model, :pre_installed_sw, :capacitystatus,
      :lease_contract_length, :offering_class, :purchase_option,
      :hourly, :upfront,
    )

    # @!attribute [r] on_demand
    #   @return [Array<OnDemandPriceChange>] Oldest first.
    # @!attribute [r] reserved
    #   @return [Array<ReservedPriceChange>] Oldest first.
    PricingHistory = Data.define(:on_demand, :reserved)

    # @!attribute [r] at
    #   @return [Time]
    # @!attribute [r] key
    #   @return [String]
    # @!attribute [r] value
    #   @return [String, nil] +nil+ means the attribute was removed.
    # @!attribute [r] region
    #   @return [String, nil] The AWS location this change applies to, or +nil+ for every region.
    AttributeChange = Data.define(:at, :key, :value, :region)
  end
end
