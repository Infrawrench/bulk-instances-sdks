# frozen_string_literal: true

require_relative "lib/infrawrench/bulk_instances/version"

Gem::Specification.new do |spec|
  spec.name = "infrawrench-bulk_instances"
  spec.version = Infrawrench::BulkInstances::VERSION
  spec.authors = ["Infrawrench LLC"]
  spec.email = ["astrid@infrawrench.com"]
  spec.summary = "AWS instance attributes and pricing (EC2, RDS, ElastiCache and more), with full history, from Infrawrench."
  spec.homepage = "https://infrawrench.com"
  spec.license = "MIT"
  spec.required_ruby_version = ">= 3.2"

  spec.metadata = {
    "homepage_uri" => spec.homepage,
    "source_code_uri" => "https://github.com/Infrawrench/bulk-instances-sdks/tree/main/ruby",
    "rubygems_mfa_required" => "true",
  }

  spec.files = Dir["lib/**/*.rb"] + %w[README.md LICENSE]
  spec.require_paths = ["lib"]

  # Calls liblzma to decompress downloads. A bundled gem, no longer a default one, since Ruby 4.0.
  spec.add_dependency "fiddle", "~> 1.1"
end
