# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # Oracle Cloud's compute pricing data, keyed by shape (+VM.Standard.E5.Flex-2-16+).
    # It decodes the same way as AWSPricingData; see the README for what Oracle Cloud's data holds.
    #
    # @!method get(instance_type)
    #   The shape with this name, or +nil+ if the bundle has never listed it.
    #   @return [OracleInstance, nil]
    # @!method [](instance_type)
    #   The same as #get.
    #   @return [OracleInstance, nil]
    class OraclePricingData < AWSPricingData
      private

      # @return [OracleInstance]
      def new_instance(name, raw)
        OracleInstance.new(name, raw, self)
      end
    end

    # One Oracle Cloud compute shape.
    class OracleInstance < AWSInstance; end
  end
end
