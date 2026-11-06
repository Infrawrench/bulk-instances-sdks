# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # Hetzner's cloud server pricing data, keyed by server type (+cx23+).
    # It decodes the same way as AWSPricingData; see the README for what Hetzner's data holds.
    #
    # @!method get(instance_type)
    #   The server type with this name, or +nil+ if the bundle has never listed it.
    #   @return [HetznerInstance, nil]
    # @!method [](instance_type)
    #   The same as #get.
    #   @return [HetznerInstance, nil]
    class HetznerPricingData < AWSPricingData
      private

      # @return [HetznerInstance]
      def new_instance(name, raw)
        HetznerInstance.new(name, raw, self)
      end
    end

    # One Hetzner cloud server type.
    class HetznerInstance < AWSInstance; end
  end
end
