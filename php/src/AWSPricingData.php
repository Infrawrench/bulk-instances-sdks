<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances;

/**
 * The AWS EC2 pricing data, keyed by instance type.
 *
 * Nothing is decoded until it is asked for: `get()` parses and wraps one instance's
 * raw rows, and each method on the returned {@see AWSInstance} decodes its part on
 * first access and keeps the result.
 *
 * @phpstan-type AttributeChangeRow array{0: int, 1: int, 2?: int|null, 3?: int|null}
 * @phpstan-type OnDemandRow array{0: int, 1: int, 2: int, 3?: int|float|null}
 * @phpstan-type ReservedRow array{0: int, 1: int, 2: int, 3: int, 4?: int|float|null, 5?: int|float|null}
 * @phpstan-type RawInstance array{0: list<array{int, int}>, 1: list<AttributeChangeRow>, 2: int|float, 3: list<OnDemandRow>, 4: list<ReservedRow>, 5: int, 6: int|null}
 * @phpstan-type BundleFile array{compression_table: list<string>, snapshots: list<int>, regions: list<array{int, list<array{int, int}>}>, variants: list<list<int>>, reserved_terms: list<list<int>>, instances: array<string, RawInstance>}
 */
final class AWSPricingData
{
    /** @var array<string, AWSInstance> */
    private array $instances = [];
    /** @var list<Variant>|null */
    private ?array $variants = null;
    /** @var list<ReservedTerm>|null */
    private ?array $terms = null;
    /** @var array<string, array<string, string>>|null */
    private ?array $regions = null;
    /** @var list<\DateTimeImmutable>|null */
    private ?array $snapshots = null;
    /** @var array<int, \DateTimeImmutable> */
    private array $dates = [];
    private ?\DateTimeZone $utc = null;
    /** @var array<string, array{int, int}>|null Offset and length of each instance's rows in `$json`. */
    private ?array $spans = null;
    private string $json = '';

    /**
     * @param BundleFile $raw The bundle as instances-bundler writes it; every string is an index into `compression_table`.
     */
    public function __construct(private readonly array $raw)
    {
    }

    /**
     * Parses a bundle file.
     *
     * Each instance's rows are only parsed when `get()` first asks for that instance:
     * as PHP arrays, a whole bundle's rows take about eight times the memory of their JSON.
     *
     * @throws \JsonException if `$json` is not a valid bundle
     */
    public static function fromJson(string $json): self
    {
        [$top, $spans] = Internal\BundleJson::split($json);
        /** @var BundleFile $raw */
        $raw = $top + ['instances' => []];
        $data = new self($raw);
        if ($spans !== null) {
            $data->spans = $spans;
            $data->json = $json;
        }
        return $data;
    }

    /**
     * Every instance type in the bundle, including ones AWS no longer lists (see {@see AWSInstance::deletedAt()}).
     *
     * @return list<string>
     */
    public function keys(): array
    {
        return array_map(strval(...), array_keys($this->spans ?? $this->raw['instances']));
    }

    public function has(string $instanceType): bool
    {
        return array_key_exists($instanceType, $this->spans ?? $this->raw['instances']);
    }

    /**
     * The instance with this type (e.g. `m5.large`), or `null` if the bundle has never listed it.
     *
     * @throws \JsonException if the instance's rows in the bundle are not valid JSON
     */
    public function get(string $instanceType): ?AWSInstance
    {
        if (!isset($this->instances[$instanceType]) && $this->has($instanceType)) {
            if ($this->spans === null) {
                $raw = $this->raw['instances'][$instanceType];
            } else {
                /** @var RawInstance $raw */
                $raw = Internal\BundleJson::decode($this->json, ...$this->spans[$instanceType]);
            }
            $this->instances[$instanceType] = new AWSInstance($instanceType, $raw, $this);
        }
        return $this->instances[$instanceType] ?? null;
    }

    /**
     * The publication date of every AWS price list in the bundle, oldest first.
     *
     * @return list<\DateTimeImmutable>
     */
    public function snapshots(): array
    {
        return $this->snapshots ??= array_map($this->date(...), $this->raw['snapshots']);
    }

    /**
     * Attributes of each AWS location (`regionCode`, `locationType`), keyed by location name.
     *
     * @return array<string, array<string, string>>
     */
    public function regions(): array
    {
        if ($this->regions === null) {
            $this->regions = [];
            foreach ($this->raw['regions'] as [$loc, $pairs]) {
                $attrs = [];
                foreach ($pairs as [$k, $v]) {
                    $attrs[$this->str($k)] = $this->str($v);
                }
                $this->regions[$this->str($loc)] = $attrs;
            }
        }
        return $this->regions;
    }

    /** @internal */
    public function str(int $i): string
    {
        return $this->raw['compression_table'][$i] ?? throw new \OutOfRangeException("string index $i out of range");
    }

    /**
     * @internal
     * @return array{string, ?string} The location name and its code, if it has one.
     */
    public function location(int $i): array
    {
        $region = $this->str($i);
        return [$region, $this->regions()[$region]['regionCode'] ?? null];
    }

    /** @internal */
    public function variant(int $i): Variant
    {
        $this->variants ??= array_map(
            fn (array $v) => new Variant(
                operatingSystem: $this->str($v[0]),
                tenancy: $this->str($v[1]),
                licenseModel: $this->str($v[2]),
                preInstalledSw: $this->str($v[3]),
                capacitystatus: $this->str($v[4]),
            ),
            $this->raw['variants'],
        );
        return $this->variants[$i] ?? throw new \OutOfRangeException("variant index $i out of range");
    }

    /** @internal */
    public function term(int $i): ReservedTerm
    {
        $this->terms ??= array_map(
            fn (array $t) => new ReservedTerm(
                leaseContractLength: $this->str($t[0]),
                offeringClass: $this->str($t[1]),
                purchaseOption: $this->str($t[2]),
            ),
            $this->raw['reserved_terms'],
        );
        return $this->terms[$i] ?? throw new \OutOfRangeException("reserved term index $i out of range");
    }

    /**
     * Dates are immutable, so every row with the same timestamp shares one.
     *
     * @internal
     */
    public function date(int|float $ts): \DateTimeImmutable
    {
        $ts = (int) $ts;
        if (!isset($this->dates[$ts])) {
            $this->utc ??= new \DateTimeZone('UTC');
            $this->dates[$ts] = (new \DateTimeImmutable("@$ts"))->setTimezone($this->utc);
        }
        return $this->dates[$ts];
    }
}
