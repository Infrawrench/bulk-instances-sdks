/**
 * AWS instance attributes and prices (EC2, RDS, ElastiCache and more), with their full history, from the bundles
 * Infrawrench publishes at {@code instances-bundles.infrawrench.com}.
 *
 * <p>Start with {@link com.infrawrench.bulkinstances.BulkInstances#downloadAwsEc2PricingData()}, or
 * {@link com.infrawrench.bulkinstances.BulkInstances#downloadAwsPricingData(String)} for another platform.
 * {@link com.infrawrench.bulkinstances.BulkInstances#downloadRunpodPricingData()},
 * {@link com.infrawrench.bulkinstances.BulkInstances#downloadAlibabaPricingData()},
 * {@link com.infrawrench.bulkinstances.BulkInstances#downloadAzurePricingData()} and
 * {@link com.infrawrench.bulkinstances.BulkInstances#downloadGcpPricingData()} load RunPod's, Alibaba Cloud's, Azure's
 * and Google Cloud's prices, in the same format.
 */
package com.infrawrench.bulkinstances;
