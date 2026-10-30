# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # One instance type. Each reader decodes on first access and caches the result.
    class AWSInstance
      # The instance type, e.g. +m5.large+.
      # @return [String]
      attr_reader :name

      def initialize(name, raw, data)
        @name = name
        @raw = raw
        @data = data
      end

      # The publication date of the first price list that listed this instance.
      # @return [Time]
      def created_at
        @created_at ||= Util.time(@raw[5])
      end

      # The publication date of the first price list that stopped listing it, or +nil+ if AWS still lists it.
      # @return [Time, nil]
      def deleted_at
        return if @raw[6].nil?

        @deleted_at ||= Util.time(@raw[6])
      end

      # The latest attributes shared by every region. Regional differences are in #attributes_in.
      # @return [Hash{String => String}]
      def attributes
        @attributes ||= attributes_history.each_with_object({}) do |c, out|
          next unless c.region.nil?

          if c.value.nil?
            out.delete(c.key)
          else
            out[c.key] = c.value
          end
        end.freeze
      end

      # The latest attributes in one AWS location (e.g. <tt>US East (N. Virginia)</tt>): the
      # global ones with that region's overrides on top. A regional override keeps
      # applying even after a newer global change to the same key.
      # @return [Hash{String => String}]
      def attributes_in(region)
        out = attributes.dup
        overrides = {}
        attributes_history.each { |c| overrides[c.key] = c.value if c.region == region }
        overrides.each do |k, v|
          if v.nil?
            out.delete(k)
          else
            out[k] = v
          end
        end
        out.freeze
      end

      # Every attribute change, oldest first, starting with the attributes the instance was first listed with.
      # @return [Array<AttributeChange>]
      def attributes_history
        @attributes_history ||= begin
          d = @data
          initial = @raw[0].map do |k, v|
            AttributeChange.new(at: created_at, key: d.str(k), value: d.str(v), region: nil)
          end
          changes = Util.sort_by_time(@raw[1]).map do |ts, key, value, region|
            AttributeChange.new(
              at: Util.time(ts),
              key: d.str(key),
              value: value.nil? ? nil : d.str(value),
              region: region.nil? ? nil : d.str(region),
            )
          end
          (initial + changes).freeze
        end
      end

      # The current price of everything still offered.
      # @return [Pricing]
      def pricing
        @pricing ||= begin
          history = pricing_history
          od = {}
          history.on_demand.each { |r| od[od_key(r)] = r }
          rs = {}
          history.reserved.each do |r|
            rs[[*od_key(r), r.lease_contract_length, r.offering_class, r.purchase_option]] = r
          end

          Pricing.new(
            on_demand: od.each_value.reject { |r| r.hourly.nil? }.map do |r|
              OnDemandPrice.new(**r.to_h.except(:at), since: r.at)
            end.freeze,
            reserved: rs.each_value.reject { |r| r.hourly.nil? }.map do |r|
              ReservedPrice.new(**r.to_h.except(:at, :upfront), upfront: r.upfront || 0.0, since: r.at)
            end.freeze,
          )
        end
      end

      # Every on-demand and reserved price change, oldest first.
      # @return [PricingHistory]
      def pricing_history
        @pricing_history ||= begin
          d = @data
          base = @raw[2].to_f
          PricingHistory.new(
            # [ts, region, variant, price: omitted = base price, null = no longer offered]
            on_demand: Util.sort_by_time(@raw[3]).map do |ts, region, variant, *price|
              OnDemandPriceChange.new(
                at: Util.time(ts),
                **d.location(region),
                **d.variant(variant).to_h,
                hourly: price.empty? ? base : price[0]&.to_f,
              )
            end.freeze,
            # [ts, region, variant, term, hourly: null = no longer offered, upfront: omitted if 0]
            reserved: Util.sort_by_time(@raw[4]).map do |ts, region, variant, term, hourly, upfront|
              removed = hourly.nil?
              ReservedPriceChange.new(
                at: Util.time(ts),
                **d.location(region),
                **d.variant(variant).to_h,
                **d.term(term).to_h,
                hourly: removed ? nil : hourly.to_f,
                upfront: removed ? nil : (upfront || 0).to_f,
              )
            end.freeze,
          )
        end
      end

      private

      def od_key(r)
        [r.region, *r.variant.values]
      end
    end
  end
end
