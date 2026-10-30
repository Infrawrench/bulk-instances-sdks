# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # One AWS platform's pricing data, keyed by instance type.
    #
    # Nothing is decoded until it is asked for: #get wraps the raw rows, and each
    # reader on the returned AWSInstance decodes its part on first access and keeps
    # the result. Everything returned is frozen and shared between calls.
    #
    # Memoization is not synchronized: threads racing on a first access may decode
    # the same part twice, which is harmless.
    class AWSPricingData
      # +raw+ is the parsed bundle as instances-bundler writes it, where every string is an
      # index into +compression_table+:
      #
      #   {
      #     "offer" => "AmazonRDS", # EC2 bundles leave it out
      #     "compression_table" => [String, ...],
      #     "snapshots" => [Integer, ...],
      #     "regions" => [[location, [[key, value], ...]], ...],
      #     "variant_keys" => [String, ...], # EC2 bundles leave it out (see EC2_VARIANT_KEYS)
      #     "variants" => [[value, ...], ...], # one value per variant key
      #     "reserved_terms" => [[lease, offering, purchase], ...],
      #     "instances" => { "m5.large" => [attrs, attr_changes, base_price, on_demand, reserved, created_at, deleted_at] },
      #   }
      def initialize(raw)
        @raw = raw
        @instances = {}
      end

      # Every instance type in the bundle, including ones AWS no longer lists (see AWSInstance#deleted_at).
      # @return [Array<String>]
      def keys
        @keys ||= @raw["instances"].keys.freeze
      end

      # @return [Boolean]
      def has?(instance_type)
        @raw["instances"].key?(instance_type)
      end
      alias key? has?

      # The instance with this type (e.g. +m5.large+), or +nil+ if the bundle has never listed it.
      # @return [AWSInstance, nil]
      def get(instance_type)
        inst = @instances[instance_type]
        if inst.nil? && has?(instance_type)
          inst = @instances[instance_type] = AWSInstance.new(instance_type, @raw["instances"][instance_type], self)
        end
        inst
      end
      alias [] get

      # The AWS offer code, e.g. +AmazonEC2+ or +AmazonRDS+.
      # @return [String]
      def offer
        @raw["offer"] || "AmazonEC2"
      end

      # The names of the fields that pick a price, which every price's +variant+ is keyed by.
      # @return [Array<String>]
      def variant_keys
        @raw["variant_keys"] || EC2_VARIANT_KEYS
      end

      # The publication date of every AWS price list in the bundle, oldest first.
      # @return [Array<Time>]
      def snapshots
        @snapshots ||= @raw["snapshots"].map { |ts| Util.time(ts) }.freeze
      end

      # Attributes of each AWS location (+regionCode+, +locationType+), keyed by location name.
      # @return [Hash{String => Hash{String => String}}]
      def regions
        @regions ||= @raw["regions"].to_h do |loc, pairs|
          [str(loc), pairs.to_h { |k, v| [str(k), str(v)] }.freeze]
        end.freeze
      end

      # @api private
      def str(i)
        s = @raw["compression_table"][i] if i.is_a?(Integer) && i >= 0
        raise IndexError, "string index #{i.inspect} out of range" if s.nil?

        s
      end

      # @api private
      # @return [Hash] +region:+ and +region_code:+
      def location(i)
        region = str(i)
        { region:, region_code: regions.dig(region, "regionCode") }
      end

      # @api private
      # @return [Variant]
      def variant(i)
        @variants ||= @raw["variants"].map do |fields|
          keys = variant_keys
          raise "variant has #{fields.length} fields, expected #{keys.length}" if fields.length != keys.length

          variant = keys.zip(fields).to_h { |k, v| [k, str(v)] }.freeze
          Variant.new(
            variant:,
            operating_system: variant.fetch("operatingSystem", ""),
            tenancy: variant.fetch("tenancy", ""),
            license_model: variant.fetch("licenseModel", ""),
            pre_installed_sw: variant.fetch("preInstalledSw", ""),
            capacitystatus: variant.fetch("capacitystatus", ""),
          )
        end.freeze
        @variants[i]
      end

      # @api private
      # @return [ReservedTerm]
      def term(i)
        @terms ||= @raw["reserved_terms"].map do |lease, offering, purchase|
          ReservedTerm.new(lease_contract_length: str(lease), offering_class: str(offering), purchase_option: str(purchase))
        end.freeze
        @terms[i]
      end
    end
  end
end
