# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # Azure's virtual machine pricing data, keyed by VM size (+Standard_D2s_v3+).
    # It decodes the same way as AWSPricingData; see the README for what Azure's data holds.
    #
    # @!method get(instance_type)
    #   The VM size with this name, or +nil+ if the bundle has never listed it.
    #   @return [AzureInstance, nil]
    # @!method [](instance_type)
    #   The same as #get.
    #   @return [AzureInstance, nil]
    class AzurePricingData < AWSPricingData
      private

      # @return [AzureInstance]
      def new_instance(name, raw)
        AzureInstance.new(name, raw, self)
      end
    end

    # One Azure virtual machine size.
    class AzureInstance < AWSInstance; end
  end
end
