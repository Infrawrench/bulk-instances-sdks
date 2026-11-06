<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/** Thrown when IBM Cloud's Virtual Server for VPC pricing data cannot be downloaded. `$status` is the HTTP status, if there was a response. */
final class IBMPricingDataException extends AWSPricingDataException
{
}
