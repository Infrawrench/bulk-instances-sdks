# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # IBM Cloud's Virtual Server for VPC pricing data, keyed by profile (+bx3d-2x10+).
    # It decodes the same way as AWSPricingData; see the README for what IBM Cloud's data holds.
    #
    # @!method get(instance_type)
    #   The profile with this name, or +nil+ if the bundle has never listed it.
    #   @return [IBMInstance, nil]
    # @!method [](instance_type)
    #   The same as #get.
    #   @return [IBMInstance, nil]
    class IBMPricingData < AWSPricingData
      private

      # @return [IBMInstance]
      def new_instance(name, raw)
        IBMInstance.new(name, raw, self)
      end
    end

    # One IBM Cloud Virtual Server for VPC profile.
    class IBMInstance < AWSInstance; end
  end
end
