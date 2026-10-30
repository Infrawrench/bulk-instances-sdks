// Package bulkinstances provides AWS instance attributes and pricing (EC2, RDS,
// ElastiCache and more), with full history, from Infrawrench.
//
// [DownloadAWSEC2PricingData] fetches the EC2 bundle Infrawrench publishes at
// instances-bundles.infrawrench.com and returns it as an [AWSPricingData], keyed
// by instance type. [DownloadAWSPricingData] fetches any other platform's bundle,
// such as "rds" (see [AWSPlatforms]). Each platform's bundle is cached under its
// own name, so loading one never evicts another.
//
// The fields that pick a price differ by platform: [AWSPricingData.VariantKeys]
// names them, and every price's [Variant.Fields] is keyed by them. The other
// [Variant] fields are EC2's, and are "" on other platforms unless the platform
// has a field with that name (RDS has licenseModel).
//
// Nothing is decoded until it is asked for. Every value an accessor returns is
// shared between calls: treat returned slices, maps and pointers as read-only.
// An [AWSPricingData] and its [AWSInstance] values are safe for concurrent use.
//
// The accessors panic if the bundle is malformed (for example, a string index out
// of range), which the Infrawrench server never sends.
package bulkinstances
