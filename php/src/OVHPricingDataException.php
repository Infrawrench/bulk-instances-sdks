<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/** Thrown when OVHcloud's Public Cloud pricing data cannot be downloaded. `$status` is the HTTP status, if there was a response. */
final class OVHPricingDataException extends AWSPricingDataException
{
}
