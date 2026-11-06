<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/** Thrown when Hetzner's Server Auction pricing data cannot be downloaded. `$status` is the HTTP status, if there was a response. */
final class HetznerAuctionPricingDataException extends AWSPricingDataException
{
}
