# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # Alibaba Cloud's ECS pricing data, keyed by instance type (+ecs.g6.large+).
    # It decodes the same way as AWSPricingData; see the README for what Alibaba's data holds.
    #
    # @!method get(instance_type)
    #   The instance type with this name, or +nil+ if the bundle has never listed it.
    #   @return [AlibabaInstance, nil]
    # @!method [](instance_type)
    #   The same as #get.
    #   @return [AlibabaInstance, nil]
    class AlibabaPricingData < AWSPricingData
      private

      # @return [AlibabaInstance]
      def new_instance(name, raw)
        AlibabaInstance.new(name, raw, self)
      end
    end

    # One Alibaba Cloud ECS instance type.
    class AlibabaInstance < AWSInstance; end
  end
end
