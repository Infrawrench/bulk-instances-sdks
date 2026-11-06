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

    # Raised when RunPod's pricing data cannot be downloaded. +status+ is the HTTP status, if there was a response.
    class RunpodPricingDataError < AWSPricingDataError; end

    # Raised when Alibaba Cloud's pricing data cannot be downloaded. +status+ is the HTTP status, if there was a
    # response.
    class AlibabaPricingDataError < AWSPricingDataError; end

    # Raised when Azure's pricing data cannot be downloaded. +status+ is the HTTP status, if there was a response.
    class AzurePricingDataError < AWSPricingDataError; end

    # Raised when Google Cloud's pricing data cannot be downloaded. +status+ is the HTTP status, if there was a
    # response.
    class GCPPricingDataError < AWSPricingDataError; end

    # Raised when Hetzner's cloud server pricing data cannot be downloaded. +status+ is the HTTP status, if there
    # was a
    # response.
    class HetznerPricingDataError < AWSPricingDataError; end

    # Raised when Hetzner's Server Auction pricing data cannot be downloaded. +status+ is the HTTP status, if
    # there was a
    # response.
    class HetznerAuctionPricingDataError < AWSPricingDataError; end

    # Raised when OVHcloud's Public Cloud pricing data cannot be downloaded. +status+ is the HTTP status, if there
    # was a
    # response.
    class OVHPricingDataError < AWSPricingDataError; end

    # Raised when OVHcloud's eco dedicated server pricing data cannot be downloaded. +status+ is the HTTP status,
    # if there was a
    # response.
    class OVHEcoPricingDataError < AWSPricingDataError; end

    # Raised when Oracle Cloud's compute pricing data cannot be downloaded. +status+ is the HTTP status, if there
    # was a
    # response.
    class OraclePricingDataError < AWSPricingDataError; end

    # Raised when IBM Cloud's Virtual Server for VPC pricing data cannot be downloaded. +status+ is the HTTP
    # status, if there was a
    # response.
    class IBMPricingDataError < AWSPricingDataError; end
  end
end
