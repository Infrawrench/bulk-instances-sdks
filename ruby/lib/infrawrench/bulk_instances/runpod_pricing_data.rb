# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # RunPod's pricing data, keyed by GPU type id (<tt>NVIDIA H100 80GB HBM3</tt>) or CPU pod id (+cpu3c-2-4+).
    # It decodes the same way as AWSPricingData; see the README for what RunPod's data holds.
    #
    # @!method get(id)
    #   The GPU type or CPU pod with this id, or +nil+ if the bundle has never listed it.
    #   @return [RunpodInstance, nil]
    # @!method [](id)
    #   The same as #get.
    #   @return [RunpodInstance, nil]
    class RunpodPricingData < AWSPricingData
      private

      # @return [RunpodInstance]
      def new_instance(name, raw)
        RunpodInstance.new(name, raw, self)
      end
    end

    # One RunPod GPU type or CPU pod.
    class RunpodInstance < AWSInstance; end
  end
end
