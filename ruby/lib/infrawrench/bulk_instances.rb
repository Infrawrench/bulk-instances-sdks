# frozen_string_literal: true

require "fileutils"
require "json"
require "net/http"
require "openssl"
require "uri"
require "zlib"

require_relative "bulk_instances/version"
require_relative "bulk_instances/error"
require_relative "bulk_instances/types"
require_relative "bulk_instances/aws_pricing_data"
require_relative "bulk_instances/aws_instance"
require_relative "bulk_instances/runpod_pricing_data"
require_relative "bulk_instances/alibaba_pricing_data"
require_relative "bulk_instances/azure_pricing_data"
require_relative "bulk_instances/gcp_pricing_data"
require_relative "bulk_instances/hetzner_pricing_data"
require_relative "bulk_instances/hetzner_auction_pricing_data"
require_relative "bulk_instances/ovh_pricing_data"
require_relative "bulk_instances/ovh_eco_pricing_data"
require_relative "bulk_instances/oracle_pricing_data"
require_relative "bulk_instances/ibm_pricing_data"

module Infrawrench
  # AWS instance attributes and pricing (EC2, RDS, ElastiCache and more), with full history, from Infrawrench.
  module BulkInstances
    DEFAULT_BASE_URL = "https://instances-bundles.infrawrench.com"
    DEFAULT_API_URL = "https://app.infrawrench.com"
    USER_AGENT = "infrawrench/bulk-instances, ruby, 1.0"

    # What Net::HTTP raises when the server cannot be reached or the connection breaks.
    TRANSPORT_ERRORS = [
      SystemCallError, SocketError, IOError, Timeout::Error, OpenSSL::SSL::SSLError,
      Net::ProtocolError, Net::HTTPBadResponse, Net::HTTPHeaderSyntaxError, Zlib::Error,
    ].freeze
    private_constant :TRANSPORT_ERRORS

    # Helpers shared by the decoders.
    module Util
      module_function

      def time(ts)
        Time.at(ts, in: "UTC").freeze
      end

      # Sorts rows by their first element (a timestamp). +sort_by+ is not stable, so the
      # index keeps rows with the same timestamp in order (later rows win).
      def sort_by_time(rows)
        rows.each_with_index.sort_by { |row, i| [row[0], i] }.map(&:first)
      end
    end
    private_constant :Util

    # The AWS platforms Infrawrench publishes a bundle for. Any other lowercase name is
    # requested as is, so a platform added later works without a new SDK.
    AWS_PLATFORMS = %w[ec2 rds elasticache opensearch redshift docdb neptune memorydb dax sagemaker emr gamelift spot].freeze

    # The variant keys of EC2 bundles, which don't list their own.
    EC2_VARIANT_KEYS = %w[operatingSystem tenancy licenseModel preInstalledSw capacitystatus].freeze

    class << self
      # Downloads the AWS EC2 pricing data. The same as <tt>download_aws_pricing_data("ec2", ...)</tt>.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [AWSPricingData]
      # @raise [AWSPricingDataError]
      def download_aws_ec2_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        download_aws_pricing_data("ec2", token:, cache_pricing_data:, cache_path:, base_url:)
      end

      # Downloads one AWS platform's pricing data compressed blob and decompresses it.
      #
      # The bucket's <tt><platform>-latest</tt> object (+latest+ for EC2) names the newest bundle. With
      # caching on, a bundle is only downloaded when that names one that is not in the cache yet,
      # and if it cannot be fetched at all (offline, outage) the newest cached bundle is used.
      #
      # @param platform [String, Symbol] One of AWS_PLATFORMS, e.g. +"rds"+, or any other lowercase platform name.
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [AWSPricingData]
      # @raise [AWSPricingDataError]
      def download_aws_pricing_data(platform, token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        AWSPricingData.new(load_bundle(platform, token:, cache_pricing_data:, cache_path:, base_url:))
      end

      # Downloads RunPod's pricing data: GPU types (priced per GPU per hour) and CPU pods (per pod per hour).
      # Caching and the offline fallback work as for #download_aws_pricing_data, and it takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [RunpodPricingData]
      # @raise [RunpodPricingDataError]
      def download_runpod_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        RunpodPricingData.new(
          load_bundle_as("runpod", RunpodPricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Downloads Alibaba Cloud's ECS pricing data: pay-as-you-go, subscription and reserved instance prices per
      # region. Caching and the offline fallback work as for #download_aws_pricing_data, and it takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [AlibabaPricingData]
      # @raise [AlibabaPricingDataError]
      def download_alibaba_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        AlibabaPricingData.new(
          load_bundle_as("alibaba", AlibabaPricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Downloads Azure's virtual machine pricing data: pay-as-you-go, Spot and Low Priority prices, reservations and
      # savings plans per region. Caching and the offline fallback work as for #download_aws_pricing_data, and it
      # takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [AzurePricingData]
      # @raise [AzurePricingDataError]
      def download_azure_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        AzurePricingData.new(
          load_bundle_as("azure", AzurePricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Downloads Google Cloud's Compute Engine pricing data: Standard and Spot prices and committed use discounts per
      # region, for each machine type. Caching and the offline fallback work as for #download_aws_pricing_data, and it
      # takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [GCPPricingData]
      # @raise [GCPPricingDataError]
      def download_gcp_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        GCPPricingData.new(
          load_bundle_as("gcp", GCPPricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Downloads Hetzner's cloud server pricing data: hourly prices and monthly caps per location, for each server
      # type. Caching and the offline fallback work as for #download_aws_pricing_data, and it
      # takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [HetznerPricingData]
      # @raise [HetznerPricingDataError]
      def download_hetzner_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        HetznerPricingData.new(
          load_bundle_as("hetzner", HetznerPricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Downloads Hetzner's Server Auction pricing data: the hourly price and monthly cap of each server for sale,
      # by listing id. Caching and the offline fallback work as for #download_aws_pricing_data, and it
      # takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [HetznerAuctionPricingData]
      # @raise [HetznerAuctionPricingDataError]
      def download_hetzner_auction_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        HetznerAuctionPricingData.new(
          load_bundle_as("hetznerauction", HetznerAuctionPricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Downloads OVHcloud's Public Cloud pricing data: hourly and monthly prices per pricing zone, for each
      # instance flavor. Caching and the offline fallback work as for #download_aws_pricing_data, and it
      # takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [OVHPricingData]
      # @raise [OVHPricingDataError]
      def download_ovh_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        OVHPricingData.new(
          load_bundle_as("ovh", OVHPricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Downloads OVHcloud's eco dedicated server pricing data: monthly rent and prepaid prices per data center and
      # configuration, for Kimsufi, So you Start, Rise and Advance servers. Caching and the offline fallback work as
      # for #download_aws_pricing_data, and it
      # takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [OVHEcoPricingData]
      # @raise [OVHEcoPricingDataError]
      def download_ovh_eco_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        OVHEcoPricingData.new(
          load_bundle_as("ovheco", OVHEcoPricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Downloads Oracle Cloud's compute pricing data: hourly prices for each VM and bare metal shape, the same in
      # every commercial region. Caching and the offline fallback work as for #download_aws_pricing_data, and it
      # takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [OraclePricingData]
      # @raise [OraclePricingDataError]
      def download_oracle_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        OraclePricingData.new(
          load_bundle_as("oracle", OraclePricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Downloads IBM Cloud's Virtual Server for VPC pricing data: on-demand, Spot, burstable and reserved prices
      # per region, for each profile. Caching and the offline fallback work as for #download_aws_pricing_data, and
      # it
      # takes the same options.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [IBMPricingData]
      # @raise [IBMPricingDataError]
      def download_ibm_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        IBMPricingData.new(
          load_bundle_as("ibm", IBMPricingDataError, token:, cache_pricing_data:, cache_path:, base_url:),
        )
      end

      # Fetches one instance from the Infrawrench API, without downloading the platform's bundle.
      # Nothing is cached.
      #
      # The result is the same as <tt>download_aws_pricing_data(platform).get(instance_type)</tt>, from
      # whichever bundle the API last synced, which can trail the newest bundle by up to half an hour.
      #
      # @param platform [String, Symbol] One of AWS_PLATFORMS, e.g. +"rds"+, or any other lowercase platform name.
      # @param instance_type [String] The instance type, e.g. +"m5.large"+.
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param base_url [String, nil] Where the Infrawrench API is served from. Defaults to https://app.infrawrench.com
      # @return [AWSInstance, nil] +nil+ if the platform has no instance with that name.
      # @raise [AWSPricingDataError]
      def fetch_aws_instance(platform, instance_type, token: nil, base_url: nil)
        fetch_instance(platform, instance_type, AWSPricingData, token:, base_url:)
      end

      # Fetches one RunPod GPU type or CPU pod from the Infrawrench API, without downloading RunPod's bundle.
      # Nothing is cached. It takes the same options as #fetch_aws_instance.
      #
      # The result is the same as <tt>download_runpod_pricing_data.get(id)</tt>, from whichever bundle the API
      # last synced, which can trail the newest bundle by up to half an hour.
      #
      # @param id [String] The GPU type id (<tt>"NVIDIA H100 80GB HBM3"</tt>) or CPU pod id (+"cpu3c-2-4"+).
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param base_url [String, nil] Where the Infrawrench API is served from. Defaults to https://app.infrawrench.com
      # @return [RunpodInstance, nil] +nil+ if RunPod has no instance with that id.
      # @raise [RunpodPricingDataError]
      def fetch_runpod_instance(id, token: nil, base_url: nil)
        with_provider_error(RunpodPricingDataError) do
          fetch_instance("runpod", id, RunpodPricingData, token:, base_url:)
        end
      end

      # Fetches one Alibaba Cloud ECS instance type from the Infrawrench API, without downloading Alibaba's
      # bundle. Nothing is cached. It takes the same options as #fetch_aws_instance.
      #
      # The result is the same as <tt>download_alibaba_pricing_data.get(instance_type)</tt>, from whichever
      # bundle the API last synced, which can trail the newest bundle by up to half an hour.
      #
      # @param instance_type [String] The instance type, e.g. +"ecs.g6.large"+.
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param base_url [String, nil] Where the Infrawrench API is served from. Defaults to https://app.infrawrench.com
      # @return [AlibabaInstance, nil] +nil+ if Alibaba has no instance type with that name.
      # @raise [AlibabaPricingDataError]
      def fetch_alibaba_instance(instance_type, token: nil, base_url: nil)
        with_provider_error(AlibabaPricingDataError) do
          fetch_instance("alibaba", instance_type, AlibabaPricingData, token:, base_url:)
        end
      end

      private

      # GETs one instance from the Infrawrench API and decodes it with +data_class+, whose +get+ gives the
      # instance type.
      def fetch_instance(platform, instance_type, data_class, token:, base_url:)
        unless (platform.is_a?(String) || platform.is_a?(Symbol)) && platform.match?(/\A[a-z0-9]+\z/)
          raise AWSPricingDataError, %("#{platform}" is not a platform name.)
        end
        raise AWSPricingDataError, "The instance type is empty." if instance_type.to_s.empty?

        token = ENV.fetch("INFRAWRENCH_API_KEY", nil) if token.nil?
        if token.nil? || token.empty?
          raise AWSPricingDataError, "No Infrawrench API token: pass `token:` or set INFRAWRENCH_API_KEY."
        end

        base_url = (base_url || DEFAULT_API_URL).sub(%r{/+\z}, "")
        # Percent-encoded, with spaces as %20: a + in a path is a plus.
        name = URI.encode_www_form_component(instance_type.to_s).gsub("+", "%20")
        begin
          json = download("#{base_url}/api/v1/aws-bulk-pricing/#{platform}/#{name}", token, &:read_body)
        rescue AWSPricingDataError => e
          return nil if e.status == 404

          raise
        end

        # The bundle's tables cut down to what this instance uses, and its row renumbered to match.
        value = JSON.parse(json.to_s.dup.force_encoding(Encoding::UTF_8), freeze: true)
        bundle = value.slice("offer", "compression_table", "regions", "variant_keys", "variants", "reserved_terms")
        bundle["snapshots"] = []
        bundle["instances"] = { value["name"] => value["instance"] }
        data_class.new(bundle).get(value["name"])
      end

      # load_bundle, failing with the provider's own error class.
      def load_bundle_as(platform, error_class, **options)
        with_provider_error(error_class) { load_bundle(platform, **options) }
      end

      # Runs the block, turning an AWSPricingDataError into the provider's own error class.
      def with_provider_error(error_class)
        yield
      rescue AWSPricingDataError => e
        # Caused by what the AWS error was caused by (or nothing), so it reads as if raised here.
        raise error_class.new(e.message, status: e.status), cause: e.cause
      end

      # Downloads (or reads from the cache) one platform's bundle, parsed.
      def load_bundle(platform, token:, cache_pricing_data:, cache_path:, base_url:)
        unless (platform.is_a?(String) || platform.is_a?(Symbol)) && platform.match?(/\A[a-z0-9]+\z/)
          raise AWSPricingDataError, %("#{platform}" is not a platform name.)
        end

        # EC2's keys have no prefix because they were published before the other platforms.
        prefix = platform.to_s == "ec2" ? "" : "#{platform}-"
        token = ENV.fetch("INFRAWRENCH_API_KEY", nil) if token.nil?
        if token.nil? || token.empty?
          raise AWSPricingDataError, "No Infrawrench API token: pass `token:` or set INFRAWRENCH_API_KEY."
        end

        base_url = (base_url || DEFAULT_BASE_URL).sub(%r{/+\z}, "")
        cache_path = (cache_path || File.join(Dir.home, ".infrawrench", "aws_pricing_data")).to_s

        begin
          latest = download("#{base_url}/#{prefix}latest", token, &:read_body).to_s.dup.force_encoding(Encoding::UTF_8).scrub.strip
          unless latest.match?(/\A[A-Za-z0-9._-]+\z/)
            raise AWSPricingDataError, %(#{prefix}latest holds "#{latest}", which is not a timestamp.)
          end

          name = "#{prefix}bundle-#{latest}.json"
        rescue StandardError => e
          # A rejected token is a real answer; anything else falls back to what we already have.
          cached = newest_cached(cache_path, prefix) if cache_pricing_data && !(e.is_a?(AWSPricingDataError) && e.status == 401)
          raise if cached.nil?

          name = cached
        end

        # The cache holds the decompressed JSON: xz decompression is most of a load, reading the file is not.
        json = read_cached(File.join(cache_path, name)) if cache_pricing_data
        if json.nil?
          require_relative "bulk_instances/xz"
          json = XZ.decompress do |xz|
            download("#{base_url}/#{name}.xz", token) { |res| res.read_body { |chunk| xz << chunk } }
          end
          if cache_pricing_data
            FileUtils.mkdir_p(cache_path)
            # Write then rename, so a crash mid-write never leaves a truncated bundle to be read next time.
            tmp = File.join(cache_path, "#{name}.#{Process.pid}.tmp")
            File.binwrite(tmp, json)
            File.rename(tmp, File.join(cache_path, name))
            # This platform's older bundles, including compressed ones cached by earlier versions of this SDK.
            Dir.each_child(cache_path) do |f|
              FileUtils.rm_f(File.join(cache_path, f)) if f != name && f.match?(/\A#{prefix}bundle-.+\.json(\.xz)?\z/)
            end
          end
        end

        JSON.parse(json, freeze: true)
      end

      # GETs +url+ and yields the successful response, retrying the 503 the bundles Worker
      # answers when it cannot reach the Infrawrench API (and the API answers when it cannot
      # reach its store).
      def download(url, token)
        uri = URI(url)
        (1..).each do |attempt|
          retry_after = nil
          Net::HTTP.start(uri.hostname, uri.port, use_ssl: uri.scheme == "https") do |http|
            request = Net::HTTP::Get.new(uri, "Authorization" => "Bearer #{token}", "User-Agent" => USER_AGENT)
            http.request(request) do |res|
              return yield res if res.is_a?(Net::HTTPSuccess)

              status = res.code.to_i
              if status == 401
                raise AWSPricingDataError.new(
                  "The Infrawrench API did not accept the token (unknown, revoked or expired).", status:,
                )
              end
              if status != 503 || attempt == 3
                raise AWSPricingDataError.new("GET #{url} failed with status #{status}.", status:)
              end

              retry_after = Float(res["Retry-After"], exception: false)
              retry_after = 5 if retry_after.nil? || retry_after.nan? || retry_after.zero?
            end
          end
          sleep([retry_after, 0].max)
        end
      rescue *TRANSPORT_ERRORS => e
        raise AWSPricingDataError, "GET #{url} failed: #{e.message}"
      end

      # The newest bundle for a platform already in the cache directory, if any.
      def newest_cached(cache_path, prefix)
        Dir.children(cache_path).grep(/\A#{prefix}bundle-.+\.json\z/).max
      rescue SystemCallError
        nil
      end

      def read_cached(path)
        File.read(path, encoding: Encoding::UTF_8)
      rescue SystemCallError
        nil
      end
    end
  end
end
