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

module Infrawrench
  # AWS EC2 instance attributes and pricing, with full history, from Infrawrench.
  module BulkInstances
    DEFAULT_BASE_URL = "https://instances-bundles.infrawrench.com"
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

    class << self
      # Downloads the AWS EC2 pricing data compressed blob and decompresses it.
      #
      # The bucket's +latest+ object names the newest bundle. With caching on, a bundle
      # is only downloaded when +latest+ names one that is not in the cache yet, and if
      # +latest+ cannot be fetched at all (offline, outage) the newest cached bundle is used.
      #
      # @param token [String, nil] Your Infrawrench API token. Defaults to the +INFRAWRENCH_API_KEY+ environment variable.
      # @param cache_pricing_data [Boolean] Whether to cache the pricing data.
      # @param cache_path [String, nil] The cache path. Defaults to <tt>~/.infrawrench/aws_pricing_data</tt>.
      # @param base_url [String, nil] Where the bundles are served from. Defaults to https://instances-bundles.infrawrench.com
      # @return [AWSPricingData]
      # @raise [AWSPricingDataError]
      def download_aws_ec2_pricing_data(token: nil, cache_pricing_data: true, cache_path: nil, base_url: nil)
        token = ENV.fetch("INFRAWRENCH_API_KEY", nil) if token.nil?
        if token.nil? || token.empty?
          raise AWSPricingDataError, "No Infrawrench API token: pass `token:` or set INFRAWRENCH_API_KEY."
        end

        base_url = (base_url || DEFAULT_BASE_URL).sub(%r{/+\z}, "")
        cache_path = (cache_path || File.join(Dir.home, ".infrawrench", "aws_pricing_data")).to_s

        begin
          latest = download("#{base_url}/latest", token, &:read_body).to_s.dup.force_encoding(Encoding::UTF_8).scrub.strip
          unless latest.match?(/\A[A-Za-z0-9._-]+\z/)
            raise AWSPricingDataError, %(latest holds "#{latest}", which is not a timestamp.)
          end

          name = "bundle-#{latest}.json"
        rescue StandardError => e
          # A rejected token is a real answer; anything else falls back to what we already have.
          cached = newest_cached(cache_path) if cache_pricing_data && !(e.is_a?(AWSPricingDataError) && e.status == 401)
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
            # Older bundles, including compressed ones cached by earlier versions of this SDK.
            Dir.each_child(cache_path) do |f|
              FileUtils.rm_f(File.join(cache_path, f)) if f != name && f.match?(/\Abundle-.+\.json(\.xz)?\z/)
            end
          end
        end

        AWSPricingData.new(JSON.parse(json, freeze: true))
      end

      private

      # GETs +url+ and yields the successful response, retrying the 503 the bundles Worker
      # answers when it cannot reach the Infrawrench API.
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

      # The newest bundle already in the cache directory, if any.
      def newest_cached(cache_path)
        Dir.children(cache_path).grep(/\Abundle-.+\.json\z/).max
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
