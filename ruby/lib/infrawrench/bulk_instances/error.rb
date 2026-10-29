# frozen_string_literal: true

module Infrawrench
  module BulkInstances
    # Raised when the pricing data cannot be downloaded. +status+ is the HTTP status, if there was a response.
    class AWSPricingDataError < StandardError
      # @return [Integer, nil]
      attr_reader :status

      def initialize(message = nil, status: nil)
        super(message)
        @status = status
      end
    end
  end
end
