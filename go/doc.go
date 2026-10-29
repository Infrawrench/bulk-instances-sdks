// Package bulkinstances provides AWS EC2 instance attributes and pricing, with full
// history, from Infrawrench.
//
// [DownloadAWSEC2PricingData] fetches the bundle Infrawrench publishes at
// instances-bundles.infrawrench.com and returns it as an [AWSPricingData], keyed
// by instance type.
//
// Nothing is decoded until it is asked for. Every value an accessor returns is
// shared between calls: treat returned slices, maps and pointers as read-only.
// An [AWSPricingData] and its [AWSInstance] values are safe for concurrent use.
//
// The accessors panic if the bundle is malformed (for example, a string index out
// of range), which the Infrawrench server never sends.
package bulkinstances
