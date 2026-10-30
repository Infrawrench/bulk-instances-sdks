<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * One instance type. Each method decodes on first access and caches the result.
 *
 * @phpstan-import-type RawInstance from AWSPricingData
 */
final class AWSInstance
{
    /** @var array<string, string>|null */
    private ?array $attributes = null;
    /** @var list<AttributeChange>|null */
    private ?array $attributesHistory = null;
    private ?Pricing $pricing = null;
    private ?PricingHistory $pricingHistory = null;

    /**
     * @internal
     * @param RawInstance $raw
     */
    public function __construct(
        /** The instance type, e.g. `m5.large`. */
        public readonly string $name,
        private readonly array $raw,
        private readonly AWSPricingData $data,
    ) {
    }

    /** The publication date of the first price list that listed this instance. */
    public function createdAt(): \DateTimeImmutable
    {
        return $this->data->date($this->raw[5]);
    }

    /** The publication date of the first price list that stopped listing it, or `null` if AWS still lists it. */
    public function deletedAt(): ?\DateTimeImmutable
    {
        return $this->raw[6] === null ? null : $this->data->date($this->raw[6]);
    }

    /**
     * The latest attributes shared by every region. Regional differences are in {@see attributesIn()}.
     *
     * @return array<string, string>
     */
    public function attributes(): array
    {
        if ($this->attributes === null) {
            $out = [];
            foreach ($this->attributesHistory() as $c) {
                if ($c->region !== null) {
                    continue;
                }
                if ($c->value === null) {
                    unset($out[$c->key]);
                } else {
                    $out[$c->key] = $c->value;
                }
            }
            $this->attributes = $out;
        }
        return $this->attributes;
    }

    /**
     * The latest attributes in one AWS location (e.g. `US East (N. Virginia)`): the
     * global ones with that region's overrides on top. A regional override keeps
     * applying even after a newer global change to the same key.
     *
     * @return array<string, string>
     */
    public function attributesIn(string $region): array
    {
        $out = $this->attributes();
        $overrides = [];
        foreach ($this->attributesHistory() as $c) {
            if ($c->region === $region) {
                $overrides[$c->key] = $c->value;
            }
        }
        foreach ($overrides as $k => $v) {
            if ($v === null) {
                unset($out[$k]);
            } else {
                $out[$k] = $v;
            }
        }
        return $out;
    }

    /**
     * Every attribute change, oldest first, starting with the attributes the instance was first listed with.
     *
     * @return list<AttributeChange>
     */
    public function attributesHistory(): array
    {
        if ($this->attributesHistory === null) {
            $d = $this->data;
            $created = $this->createdAt();
            $out = [];
            foreach ($this->raw[0] as [$k, $v]) {
                $out[] = new AttributeChange(at: $created, key: $d->str($k), value: $d->str($v), region: null);
            }
            $changes = $this->raw[1];
            // Stable, so rows with the same timestamp keep their order (later rows win).
            usort($changes, self::byTime(...));
            foreach ($changes as $row) {
                $out[] = new AttributeChange(
                    at: $this->data->date($row[0]),
                    key: $d->str($row[1]),
                    value: isset($row[2]) ? $d->str($row[2]) : null,
                    region: isset($row[3]) ? $d->str($row[3]) : null,
                );
            }
            $this->attributesHistory = $out;
        }
        return $this->attributesHistory;
    }

    /** The current price of everything still offered. */
    public function pricing(): Pricing
    {
        if ($this->pricing === null) {
            $history = $this->pricingHistory();
            $od = [];
            foreach ($history->onDemand as $r) {
                $od[self::odKey($r)] = $r;
            }
            $rs = [];
            foreach ($history->reserved as $r) {
                $rs[self::odKey($r) . "\0{$r->leaseContractLength}\0{$r->offeringClass}\0{$r->purchaseOption}"] = $r;
            }

            $onDemand = [];
            foreach ($od as $r) {
                if ($r->hourly !== null) {
                    $onDemand[] = new OnDemandPrice(
                        $r->region, $r->regionCode,
                        $r->operatingSystem, $r->tenancy, $r->licenseModel, $r->preInstalledSw, $r->capacitystatus,
                        hourly: $r->hourly,
                        since: $r->at,
                        variant: $r->variant,
                    );
                }
            }
            $reserved = [];
            foreach ($rs as $r) {
                if ($r->hourly !== null) {
                    $reserved[] = new ReservedPrice(
                        $r->region, $r->regionCode,
                        $r->operatingSystem, $r->tenancy, $r->licenseModel, $r->preInstalledSw, $r->capacitystatus,
                        $r->leaseContractLength, $r->offeringClass, $r->purchaseOption,
                        hourly: $r->hourly,
                        upfront: $r->upfront ?? 0.0,
                        since: $r->at,
                        variant: $r->variant,
                    );
                }
            }
            $this->pricing = new Pricing($onDemand, $reserved);
        }
        return $this->pricing;
    }

    /** Every on-demand and reserved price change, oldest first. */
    public function pricingHistory(): PricingHistory
    {
        if ($this->pricingHistory === null) {
            $d = $this->data;
            $base = (float) $this->raw[2];

            // [ts, region, variant, price: omitted = base price, null = no longer offered]
            $rows = $this->raw[3];
            usort($rows, self::byTime(...));
            $onDemand = [];
            foreach ($rows as $row) {
                [$region, $regionCode] = $d->location($row[1]);
                $v = $d->variant($row[2]);
                $price = count($row) > 3 ? $row[3] : $base;
                $onDemand[] = new OnDemandPriceChange(
                    $region, $regionCode,
                    $v->operatingSystem, $v->tenancy, $v->licenseModel, $v->preInstalledSw, $v->capacitystatus,
                    at: $this->data->date($row[0]),
                    hourly: $price === null ? null : (float) $price,
                    variant: $v->variant,
                );
            }

            // [ts, region, variant, term, hourly: null = no longer offered, upfront: omitted if 0]
            $rows = $this->raw[4];
            usort($rows, self::byTime(...));
            $reserved = [];
            foreach ($rows as $row) {
                [$region, $regionCode] = $d->location($row[1]);
                $v = $d->variant($row[2]);
                $t = $d->term($row[3]);
                $hourly = $row[4] ?? null;
                $reserved[] = new ReservedPriceChange(
                    $region, $regionCode,
                    $v->operatingSystem, $v->tenancy, $v->licenseModel, $v->preInstalledSw, $v->capacitystatus,
                    $t->leaseContractLength, $t->offeringClass, $t->purchaseOption,
                    at: $this->data->date($row[0]),
                    hourly: $hourly === null ? null : (float) $hourly,
                    upfront: $hourly === null ? null : (float) ($row[5] ?? 0),
                    variant: $v->variant,
                );
            }

            $this->pricingHistory = new PricingHistory($onDemand, $reserved);
        }
        return $this->pricingHistory;
    }

    /**
     * @param array{0: int} $a
     * @param array{0: int} $b
     */
    private static function byTime(array $a, array $b): int
    {
        return $a[0] <=> $b[0];
    }

    /** The location and the whole variant: EC2's five fields alone would merge, say, RDS's Single-AZ and Multi-AZ prices. */
    private static function odKey(OnDemandPriceChange|ReservedPriceChange $r): string
    {
        return implode("\0", [$r->region, ...array_values($r->variant)]);
    }
}
