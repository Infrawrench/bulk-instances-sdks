"""AWS instance attributes and prices, with their full history, from Infrawrench."""

from ._data import (
    EC2_VARIANT_KEYS,
    AttributeChange,
    AWSInstance,
    AWSPricingData,
    BundleFile,
    OnDemandPrice,
    OnDemandPriceChange,
    Pricing,
    PricingHistory,
    ReservedPrice,
    ReservedPriceChange,
    ReservedTerm,
    Variant,
)
from ._download import (
    AWS_PLATFORMS,
    AWSPricingDataError,
    download_aws_ec2_pricing_data,
    download_aws_pricing_data,
    fetch_aws_instance,
)

__all__ = [
    "AWS_PLATFORMS",
    "AWSInstance",
    "AWSPricingData",
    "AWSPricingDataError",
    "AttributeChange",
    "BundleFile",
    "EC2_VARIANT_KEYS",
    "OnDemandPrice",
    "OnDemandPriceChange",
    "Pricing",
    "PricingHistory",
    "ReservedPrice",
    "ReservedPriceChange",
    "ReservedTerm",
    "Variant",
    "download_aws_ec2_pricing_data",
    "download_aws_pricing_data",
    "fetch_aws_instance",
]
