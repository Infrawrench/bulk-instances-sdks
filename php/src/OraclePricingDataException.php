<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/** Thrown when Oracle Cloud's compute pricing data cannot be downloaded. `$status` is the HTTP status, if there was a response. */
final class OraclePricingDataException extends AWSPricingDataException
{
}
