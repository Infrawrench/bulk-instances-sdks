# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # OVHcloud's Public Cloud pricing data, keyed by flavor (+b3-8+).
    # It decodes the same way as AWSPricingData; see the README for what OVHcloud's data holds.
    #
    # @!method get(instance_type)
    #   The flavor with this name, or +nil+ if the bundle has never listed it.
    #   @return [OVHInstance, nil]
    # @!method [](instance_type)
    #   The same as #get.
    #   @return [OVHInstance, nil]
    class OVHPricingData < AWSPricingData
      private

      # @return [OVHInstance]
      def new_instance(name, raw)
        OVHInstance.new(name, raw, self)
      end
    end

    # One OVHcloud Public Cloud flavor.
    class OVHInstance < AWSInstance; end
  end
end
