from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import cached_property
from types import MappingProxyType
from typing import Any, Final, TypedDict


class _BundleFileFields(TypedDict):
    compression_table: list[str]
    snapshots: list[int]
    regions: list[tuple[int, list[tuple[int, int]]]]
    variants: list[list[int]]
    reserved_terms: list[list[int]]
    # [attrs, attr_changes, base_price, on_demand, reserved, created_at, deleted_at]
    instances: dict[str, list[Any]]


class BundleFile(_BundleFileFields, total=False):
    """The bundle as instances-bundler writes it; every string is an index into ``compression_table``."""

    offer: str
    """The AWS offer code. EC2 bundles leave it out."""
    variant_keys: list[str]
    """The names of each variant's fields. EC2 bundles leave it out (see :data:`EC2_VARIANT_KEYS`)."""


EC2_VARIANT_KEYS: Final[tuple[str, ...]] = (
    "operatingSystem", "tenancy", "licenseModel", "preInstalledSw", "capacitystatus",
)
"""The variant keys of EC2 bundles, which don't list their own."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Variant:
    """The product fields that pick a price."""

    variant: Mapping[str, str] = field(hash=False)
    """Every field that picks the price, keyed by name, in :attr:`AWSPricingData.variant_keys` order:
    for RDS, ``databaseEngine``, ``deploymentOption`` and so on."""
    operating_system: str
    """EC2's variant fields. For other platforms these are ``""`` unless the platform shares the field."""
    tenancy: str
    license_model: str
    pre_installed_sw: str
    capacitystatus: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ReservedTerm:
    lease_contract_length: str
    offering_class: str
    purchase_option: str


@dataclass(frozen=True, slots=True, kw_only=True)
class OnDemandPrice:
    region: str
    """The AWS location name, e.g. ``US East (N. Virginia)``."""
    region_code: str | None
    """e.g. ``us-east-1``. ``None`` for locations the price list never gave a code."""
    variant: Mapping[str, str] = field(hash=False)
    """Every field that picks the price, keyed by name, in :attr:`AWSPricingData.variant_keys` order."""
    operating_system: str
    """EC2's variant fields. For other platforms these are ``""`` unless the platform shares the field."""
    tenancy: str
    license_model: str
    pre_installed_sw: str
    capacitystatus: str
    hourly: float
    """USD per hour."""
    since: datetime
    """When this price took effect."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ReservedPrice:
    region: str
    """The AWS location name, e.g. ``US East (N. Virginia)``."""
    region_code: str | None
    """e.g. ``us-east-1``. ``None`` for locations the price list never gave a code."""
    variant: Mapping[str, str] = field(hash=False)
    """Every field that picks the price, keyed by name, in :attr:`AWSPricingData.variant_keys` order."""
    operating_system: str
    """EC2's variant fields. For other platforms these are ``""`` unless the platform shares the field."""
    tenancy: str
    license_model: str
    pre_installed_sw: str
    capacitystatus: str
    lease_contract_length: str
    offering_class: str
    purchase_option: str
    hourly: float
    """USD per hour."""
    upfront: float
    """USD paid up front."""
    since: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class Pricing:
    on_demand: tuple[OnDemandPrice, ...]
    reserved: tuple[ReservedPrice, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class OnDemandPriceChange:
    at: datetime
    region: str
    """The AWS location name, e.g. ``US East (N. Virginia)``."""
    region_code: str | None
    """e.g. ``us-east-1``. ``None`` for locations the price list never gave a code."""
    variant: Mapping[str, str] = field(hash=False)
    """Every field that picks the price, keyed by name, in :attr:`AWSPricingData.variant_keys` order."""
    operating_system: str
    """EC2's variant fields. For other platforms these are ``""`` unless the platform shares the field."""
    tenancy: str
    license_model: str
    pre_installed_sw: str
    capacitystatus: str
    hourly: float | None
    """``None`` means no longer offered from ``at`` on."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ReservedPriceChange:
    at: datetime
    region: str
    """The AWS location name, e.g. ``US East (N. Virginia)``."""
    region_code: str | None
    """e.g. ``us-east-1``. ``None`` for locations the price list never gave a code."""
    variant: Mapping[str, str] = field(hash=False)
    """Every field that picks the price, keyed by name, in :attr:`AWSPricingData.variant_keys` order."""
    operating_system: str
    """EC2's variant fields. For other platforms these are ``""`` unless the platform shares the field."""
    tenancy: str
    license_model: str
    pre_installed_sw: str
    capacitystatus: str
    lease_contract_length: str
    offering_class: str
    purchase_option: str
    hourly: float | None
    """``None`` means no longer offered from ``at`` on."""
    upfront: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PricingHistory:
    on_demand: tuple[OnDemandPriceChange, ...]
    """Oldest first."""
    reserved: tuple[ReservedPriceChange, ...]
    """Oldest first."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeChange:
    at: datetime
    key: str
    value: str | None
    """``None`` means the attribute was removed."""
    region: str | None
    """The AWS location this change applies to, or ``None`` for every region."""


def _date(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _pad(row: Sequence[Any], n: int) -> list[Any]:
    # Trailing elements may be omitted; they read as null.
    return [*row, *[None] * (n - len(row))]


def _price(x: float | None) -> float | None:
    # JSON gives whole prices as integers (`2`, `0`).
    return None if x is None else float(x)


class AWSPricingData:
    """One AWS platform's pricing data, keyed by instance type.

    Nothing is decoded until it is asked for: :meth:`get` wraps the raw rows, and each
    property on the returned :class:`AWSInstance` decodes its part on first access
    and keeps the result.

    Decoding is not synchronized: threads that first touch the same part at the same
    time may each decode it, which is harmless but wasted work.
    """

    def __init__(self, raw: BundleFile | Mapping[str, Any]) -> None:
        self._raw: Mapping[str, Any] = raw
        self._table: list[str] = raw["compression_table"]
        self._instances: dict[str, AWSInstance] = {}

    def keys(self) -> list[str]:
        """Every instance type in the bundle, including ones AWS no longer lists (see :attr:`AWSInstance.deleted_at`)."""
        return list(self._raw["instances"])

    def has(self, instance_type: str) -> bool:
        return instance_type in self._raw["instances"]

    def __contains__(self, instance_type: object) -> bool:
        return instance_type in self._raw["instances"]

    def get(self, instance_type: str) -> AWSInstance | None:
        """The instance with this type (e.g. ``m5.large``), or ``None`` if the bundle has never listed it."""
        inst = self._instances.get(instance_type)
        if inst is None and self.has(instance_type):
            inst = AWSInstance(instance_type, self._raw["instances"][instance_type], self)
            self._instances[instance_type] = inst
        return inst

    @property
    def offer(self) -> str:
        """The AWS offer code, e.g. ``AmazonEC2`` or ``AmazonRDS``."""
        offer: str | None = self._raw.get("offer")
        return "AmazonEC2" if offer is None else offer

    @cached_property
    def variant_keys(self) -> tuple[str, ...]:
        """The names of the fields that pick a price, which every price's ``variant`` is keyed by."""
        keys: list[str] | None = self._raw.get("variant_keys")
        return EC2_VARIANT_KEYS if keys is None else tuple(keys)

    @property
    def snapshots(self) -> list[datetime]:
        """The publication date of every AWS price list in the bundle, oldest first."""
        return [_date(ts) for ts in self._raw["snapshots"]]

    @cached_property
    def regions(self) -> Mapping[str, Mapping[str, str]]:
        """Attributes of each AWS location (``regionCode``, ``locationType``), keyed by location name."""
        return MappingProxyType({
            self._str(loc): MappingProxyType({self._str(k): self._str(v) for k, v in pairs})
            for loc, pairs in self._raw["regions"]
        })

    def _str(self, i: int) -> str:
        if not 0 <= i < len(self._table):
            raise IndexError(f"string index {i} out of range")
        return self._table[i]

    def _location(self, i: int) -> tuple[str, str | None]:
        """The location name and its ``regionCode``, if it has one."""
        region = self._str(i)
        attrs = self.regions.get(region)
        return region, None if attrs is None else attrs.get("regionCode")

    @cached_property
    def _variants(self) -> list[Variant]:
        keys = self.variant_keys
        out: list[Variant] = []
        for fields in self._raw["variants"]:
            if len(fields) != len(keys):
                raise ValueError(f"variant has {len(fields)} fields, expected {len(keys)}")
            variant = {k: self._str(i) for k, i in zip(keys, fields)}
            out.append(Variant(
                variant=MappingProxyType(variant),
                operating_system=variant.get("operatingSystem", ""),
                tenancy=variant.get("tenancy", ""),
                license_model=variant.get("licenseModel", ""),
                pre_installed_sw=variant.get("preInstalledSw", ""),
                capacitystatus=variant.get("capacitystatus", ""),
            ))
        return out

    @cached_property
    def _terms(self) -> list[ReservedTerm]:
        return [
            ReservedTerm(
                lease_contract_length=self._str(lease),
                offering_class=self._str(offering),
                purchase_option=self._str(purchase),
            )
            for lease, offering, purchase in self._raw["reserved_terms"]
        ]


class AWSInstance:
    """One instance type. Each property decodes on first access and caches the result."""

    name: str
    """The instance type, e.g. ``m5.large``."""

    def __init__(self, name: str, raw: Sequence[Any], data: AWSPricingData) -> None:
        self.name = name
        self._raw = raw
        self._data = data

    def __repr__(self) -> str:
        return f"AWSInstance({self.name!r})"

    @property
    def created_at(self) -> datetime:
        """The publication date of the first price list that listed this instance."""
        return _date(self._raw[5])

    @property
    def deleted_at(self) -> datetime | None:
        """The publication date of the first price list that stopped listing it, or ``None`` if AWS still lists it."""
        return None if self._raw[6] is None else _date(self._raw[6])

    @cached_property
    def attributes(self) -> Mapping[str, str]:
        """The latest attributes shared by every region. Regional differences are in :meth:`attributes_in`."""
        out: dict[str, str] = {}
        for c in self.attributes_history:
            if c.region is not None:
                continue
            if c.value is None:
                out.pop(c.key, None)
            else:
                out[c.key] = c.value
        return MappingProxyType(out)

    def attributes_in(self, region: str) -> dict[str, str]:
        """The latest attributes in one AWS location (e.g. ``US East (N. Virginia)``): the
        global ones with that region's overrides on top. A regional override keeps
        applying even after a newer global change to the same key.
        """
        out = dict(self.attributes)
        overrides: dict[str, str | None] = {}
        for c in self.attributes_history:
            if c.region == region:
                overrides[c.key] = c.value
        for k, v in overrides.items():
            if v is None:
                out.pop(k, None)
            else:
                out[k] = v
        return out

    @cached_property
    def attributes_history(self) -> tuple[AttributeChange, ...]:
        """Every attribute change, oldest first, starting with the attributes the instance was first listed with."""
        d = self._data
        created = self.created_at
        initial = [AttributeChange(at=created, key=d._str(k), value=d._str(v), region=None) for k, v in self._raw[0]]
        changes: list[AttributeChange] = []
        for row in self._raw[1]:
            # [ts, key, value: missing or null = removed, region: missing or null = every region]
            ts, key, value, region = _pad(row, 4)
            changes.append(AttributeChange(
                at=_date(ts),
                key=d._str(key),
                value=None if value is None else d._str(value),
                region=None if region is None else d._str(region),
            ))
        # Stable, so rows with the same timestamp keep their order (later rows win).
        changes.sort(key=lambda c: c.at)
        return tuple(initial + changes)

    @cached_property
    def pricing(self) -> Pricing:
        """The current price of everything still offered."""
        history = self.pricing_history
        od: dict[tuple[str, ...], OnDemandPriceChange] = {}
        for r in history.on_demand:
            od[_od_key(r)] = r
        rs: dict[tuple[str, ...], ReservedPriceChange] = {}
        for rr in history.reserved:
            rs[_od_key(rr) + (rr.lease_contract_length, rr.offering_class, rr.purchase_option)] = rr

        return Pricing(
            on_demand=tuple(
                OnDemandPrice(
                    region=r.region,
                    region_code=r.region_code,
                    variant=r.variant,
                    operating_system=r.operating_system,
                    tenancy=r.tenancy,
                    license_model=r.license_model,
                    pre_installed_sw=r.pre_installed_sw,
                    capacitystatus=r.capacitystatus,
                    hourly=r.hourly,
                    since=r.at,
                )
                for r in od.values()
                if r.hourly is not None
            ),
            reserved=tuple(
                ReservedPrice(
                    region=r.region,
                    region_code=r.region_code,
                    variant=r.variant,
                    operating_system=r.operating_system,
                    tenancy=r.tenancy,
                    license_model=r.license_model,
                    pre_installed_sw=r.pre_installed_sw,
                    capacitystatus=r.capacitystatus,
                    lease_contract_length=r.lease_contract_length,
                    offering_class=r.offering_class,
                    purchase_option=r.purchase_option,
                    hourly=r.hourly,
                    upfront=0.0 if r.upfront is None else r.upfront,
                    since=r.at,
                )
                for r in rs.values()
                if r.hourly is not None
            ),
        )

    @cached_property
    def pricing_history(self) -> PricingHistory:
        """Every on-demand and reserved price change, oldest first."""
        d = self._data
        base = float(self._raw[2])

        on_demand: list[OnDemandPriceChange] = []
        # [ts, region, variant, price: omitted = base price, null = no longer offered]
        for ts, region, variant, *price in self._raw[3]:
            name, code = d._location(region)
            v = d._variants[variant]
            on_demand.append(OnDemandPriceChange(
                at=_date(ts),
                region=name,
                region_code=code,
                variant=v.variant,
                operating_system=v.operating_system,
                tenancy=v.tenancy,
                license_model=v.license_model,
                pre_installed_sw=v.pre_installed_sw,
                capacitystatus=v.capacitystatus,
                hourly=base if not price else _price(price[0]),
            ))

        reserved: list[ReservedPriceChange] = []
        # [ts, region, variant, term, hourly: null = no longer offered, upfront: omitted if 0]
        for row in self._raw[4]:
            ts, region, variant, term, hourly, upfront = _pad(row, 6)
            removed = hourly is None
            name, code = d._location(region)
            v = d._variants[variant]
            t = d._terms[term]
            reserved.append(ReservedPriceChange(
                at=_date(ts),
                region=name,
                region_code=code,
                variant=v.variant,
                operating_system=v.operating_system,
                tenancy=v.tenancy,
                license_model=v.license_model,
                pre_installed_sw=v.pre_installed_sw,
                capacitystatus=v.capacitystatus,
                lease_contract_length=t.lease_contract_length,
                offering_class=t.offering_class,
                purchase_option=t.purchase_option,
                hourly=None if removed else _price(hourly),
                upfront=None if removed else _price(0 if upfront is None else upfront),
            ))

        # Stable, so rows with the same timestamp keep their order (later rows win).
        on_demand.sort(key=lambda c: c.at)
        reserved.sort(key=lambda c: c.at)
        return PricingHistory(on_demand=tuple(on_demand), reserved=tuple(reserved))


def _od_key(r: OnDemandPriceChange | ReservedPriceChange) -> tuple[str, ...]:
    return (r.region, *r.variant.values())
