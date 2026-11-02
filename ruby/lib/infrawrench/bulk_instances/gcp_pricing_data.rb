# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # Google Cloud's Compute Engine pricing data, keyed by machine type (+n2-standard-2+).
    # It decodes the same way as AWSPricingData; see the README for what Google Cloud's data holds.
    #
    # @!method get(instance_type)
    #   The machine type with this name, or +nil+ if the bundle has never listed it.
    #   @return [GCPInstance, nil]
    # @!method [](instance_type)
    #   The same as #get.
    #   @return [GCPInstance, nil]
    class GCPPricingData < AWSPricingData
      private

      # @return [GCPInstance]
      def new_instance(name, raw)
        GCPInstance.new(name, raw, self)
      end
    end

    # One Google Cloud Compute Engine machine type.
    class GCPInstance < AWSInstance; end
  end
end
