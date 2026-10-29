<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/** Thrown when the pricing data cannot be downloaded. `$status` is the HTTP status, if there was a response. */
class AWSPricingDataException extends \RuntimeException
{
    public function __construct(string $message, public readonly ?int $status = null, ?\Throwable $previous = null)
    {
        parent::__construct($message, $status ?? 0, $previous);
    }
}
