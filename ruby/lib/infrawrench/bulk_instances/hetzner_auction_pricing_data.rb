# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # Hetzner's Server Auction pricing data, keyed by listing (+3107671+).
    # It decodes the same way as AWSPricingData; see the README for what Hetzner's data holds.
    #
    # @!method get(instance_type)
    #   The listing with this name, or +nil+ if the bundle has never listed it.
    #   @return [HetznerAuctionInstance, nil]
    # @!method [](instance_type)
    #   The same as #get.
    #   @return [HetznerAuctionInstance, nil]
    class HetznerAuctionPricingData < AWSPricingData
      private

      # @return [HetznerAuctionInstance]
      def new_instance(name, raw)
        HetznerAuctionInstance.new(name, raw, self)
      end
    end

    # One Hetzner Server Auction listing.
    class HetznerAuctionInstance < AWSInstance; end
  end
end
