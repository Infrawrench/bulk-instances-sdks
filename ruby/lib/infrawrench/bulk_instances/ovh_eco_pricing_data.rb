# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # OVHcloud's eco dedicated server pricing data, keyed by server (+24sys01+).
    # It decodes the same way as AWSPricingData; see the README for what OVHcloud's data holds.
    #
    # @!method get(instance_type)
    #   The server with this name, or +nil+ if the bundle has never listed it.
    #   @return [OVHEcoInstance, nil]
    # @!method [](instance_type)
    #   The same as #get.
    #   @return [OVHEcoInstance, nil]
    class OVHEcoPricingData < AWSPricingData
      private

      # @return [OVHEcoInstance]
      def new_instance(name, raw)
        OVHEcoInstance.new(name, raw, self)
      end
    end

    # One OVHcloud eco dedicated server.
    class OVHEcoInstance < AWSInstance; end
  end
end
