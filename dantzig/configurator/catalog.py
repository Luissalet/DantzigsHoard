"""Catalog model for the constraint configurator.

A catalog has *slots* (decisions such as motor, power supply, enclosure). Each
slot offers *options* with attributes, price, stock and quantity. Optional
slots may stay empty. *Rules* relate options across slots.

Selectors pick a subset of a slot's values::

    {"slot": "motor", "option": "m3"}
    {"slot": "motor", "options": ["m3", "m4"]}
    {"slot": "motor", "attr": "power_w", "op": ">", "value": 1000}
    {"slot": "brake", "chosen": true}      # any option (not empty)
    {"slot": "brake", "chosen": false}     # left empty (optional slots)

Rule types:

``requires``  if ``if`` selector holds then ``then`` selector holds.
``excludes``  ``a`` and ``b`` selectors cannot hold together.
``compare``   when both slots are filled: ``left.attr op factor*right.attr + offset``
              (``right`` may be ``{"value": v}`` for a constant).
``sum``       sum of ``attr`` over the filled ``slots`` ``op`` ``value`` or
              ``op factor*bound.attr`` (``bound`` = {"slot", "attr"}).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

NONE = None  # value of an empty optional slot
OPS = ("<", "<=", "==", "!=", ">=", ">")
RULE_TYPES = ("requires", "excludes", "compare", "sum")


class CatalogError(ValueError):
    """Raised when a catalog definition is inconsistent."""


@dataclass
class Option:
    id: str
    label: str
    price: Fraction = Fraction(0)
    stock: int | None = None  # None = not tracked
    qty: int = 1
    attrs: dict[str, Any] = field(default_factory=dict)

    def available(self) -> bool:
        return self.stock is None or self.stock >= self.qty


@dataclass
class Slot:
    id: str
    label: str
    required: bool
    options: list[Option]

    def option(self, oid: str) -> Option:
        for o in self.options:
            if o.id == oid:
                return o
        raise CatalogError(f"slot {self.id!r} has no option {oid!r}")

    def values(self) -> list[str | None]:
        vals: list[str | None] = [o.id for o in self.options]
        if not self.required:
            vals.append(NONE)
        return vals


@dataclass
class Rule:
    id: str
    type: str
    label: str
    spec: dict[str, Any]


@dataclass
class Catalog:
    id: str
    name: str
    currency: str
    slots: list[Slot]
    rules: list[Rule]
    stock_policy: str = "strict"  # strict: unavailable options cannot be used

    def slot(self, sid: str) -> Slot:
        for s in self.slots:
            if s.id == sid:
                return s
        raise CatalogError(f"unknown slot {sid!r}")

    def slot_ids(self) -> list[str]:
        return [s.id for s in self.slots]

    def rule(self, rid: str) -> Rule:
        for r in self.rules:
            if r.id == rid:
                return r
        raise CatalogError(f"unknown rule {rid!r}")

    def to_dict(self) -> dict[str, Any]:
        num = exact_number

        return {
            "id": self.id,
            "name": self.name,
            "currency": self.currency,
            "stock_policy": self.stock_policy,
            "slots": [
                {
                    "id": s.id,
                    "label": s.label,
                    "required": s.required,
                    "options": [
                        {
                            "id": o.id,
                            "label": o.label,
                            "price": num(o.price),
                            "stock": o.stock,
                            "qty": o.qty,
                            "attrs": dict(o.attrs),
                        }
                        for o in s.options
                    ],
                }
                for s in self.slots
            ],
            "rules": [dict(r.spec, id=r.id, type=r.type, label=r.label) for r in self.rules],
        }


def exact_number(x: Fraction) -> int | float | str:
    """JSON form that reloads to exactly ``x``: int, exact float, or ``"p/q"``."""
    if x.denominator == 1:
        return int(x)
    f = float(x)
    if Fraction(repr(f)) == x:
        return f
    return f"{x.numerator}/{x.denominator}"


def to_fraction(value: Any, where: str) -> Fraction:
    if isinstance(value, bool):
        raise CatalogError(f"{where}: expected a number, got a boolean")
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CatalogError(f"{where}: {value!r} is not a finite number")
        return Fraction(repr(value))
    if isinstance(value, str):
        try:
            return Fraction(value.strip())
        except (ValueError, ZeroDivisionError) as exc:
            raise CatalogError(f"{where}: {value!r} is not a number") from exc
    raise CatalogError(f"{where}: expected a number, got {type(value).__name__}")


def _int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise CatalogError(f"{where}: expected an integer")
    try:
        f = to_fraction(value, where)
    except CatalogError:
        raise CatalogError(f"{where}: expected an integer") from None
    if f.denominator != 1:
        raise CatalogError(f"{where}: expected an integer, got {value!r}")
    return int(f)


def _check_selector(cat: Catalog, sel: Any, where: str) -> None:
    if not isinstance(sel, dict) or "slot" not in sel:
        raise CatalogError(f"{where}: selector needs a 'slot'")
    slot = cat.slot(sel["slot"])
    keys = {"option", "options", "attr", "chosen"} & set(sel)
    if len(keys) != 1:
        raise CatalogError(f"{where}: selector needs exactly one of option/options/attr/chosen")
    if "option" in sel:
        slot.option(sel["option"])
    elif "options" in sel:
        if not sel["options"]:
            raise CatalogError(f"{where}: empty 'options'")
        for oid in sel["options"]:
            slot.option(oid)
    elif "attr" in sel:
        if sel.get("op") not in OPS or "value" not in sel:
            raise CatalogError(f"{where}: attribute selector needs op and value")
    elif "chosen" in sel:
        if sel["chosen"] is False and slot.required:
            raise CatalogError(f"{where}: slot {slot.id!r} is required and can never be empty")


def load_catalog(data: dict[str, Any]) -> Catalog:
    """Build and validate a :class:`Catalog` from plain JSON data."""
    if not isinstance(data, dict):
        raise CatalogError("catalog must be an object")
    slots: list[Slot] = []
    seen: set[str] = set()
    for i, s in enumerate(data.get("slots") or []):
        sid = str(s.get("id") or "").strip()
        if not sid:
            raise CatalogError(f"slot #{i} has no id")
        if sid in seen:
            raise CatalogError(f"duplicate slot {sid!r}")
        seen.add(sid)
        opts: list[Option] = []
        oseen: set[str] = set()
        for j, o in enumerate(s.get("options") or []):
            oid = str(o.get("id") or "").strip()
            if not oid:
                raise CatalogError(f"slot {sid!r} option #{j} has no id")
            if oid in oseen:
                raise CatalogError(f"slot {sid!r}: duplicate option {oid!r}")
            oseen.add(oid)
            stock = o.get("stock")
            qty = _int(o.get("qty", 1), f"{sid}.{oid}.qty")
            if stock is not None:
                stock = _int(stock, f"{sid}.{oid}.stock")
            if qty < 1:
                raise CatalogError(f"{sid}.{oid}: qty must be >= 1")
            opts.append(
                Option(
                    id=oid,
                    label=str(o.get("label") or oid),
                    price=to_fraction(o.get("price", 0), f"{sid}.{oid}.price"),
                    stock=stock,
                    qty=qty,
                    attrs=dict(o.get("attrs") or {}),
                )
            )
        if not opts:
            raise CatalogError(f"slot {sid!r} has no options")
        slots.append(Slot(id=sid, label=str(s.get("label") or sid), required=bool(s.get("required", True)), options=opts))
    if not slots:
        raise CatalogError("catalog has no slots")
    policy = data.get("stock_policy", "strict")
    if policy not in ("strict", "ignore"):
        raise CatalogError("stock_policy must be 'strict' or 'ignore'")
    cat = Catalog(
        id=str(data.get("id") or "catalog"),
        name=str(data.get("name") or data.get("id") or "Catálogo"),
        currency=str(data.get("currency") or "EUR"),
        slots=slots,
        rules=[],
        stock_policy=policy,
    )
    rseen: set[str] = set()
    for i, r in enumerate(data.get("rules") or []):
        rid = str(r.get("id") or f"r{i + 1}")
        if rid in rseen:
            raise CatalogError(f"duplicate rule {rid!r}")
        if rid.startswith("__"):
            raise CatalogError(f"rule id {rid!r} is reserved")
        rseen.add(rid)
        rtype = r.get("type")
        if rtype not in RULE_TYPES:
            raise CatalogError(f"rule {rid!r}: unknown type {rtype!r}")
        spec = {k: v for k, v in r.items() if k not in ("id", "type", "label")}
        where = f"rule {rid!r}"
        if rtype == "requires":
            _check_selector(cat, spec.get("if"), where + ".if")
            _check_selector(cat, spec.get("then"), where + ".then")
        elif rtype == "excludes":
            _check_selector(cat, spec.get("a"), where + ".a")
            _check_selector(cat, spec.get("b"), where + ".b")
        elif rtype == "compare":
            left = spec.get("left") or {}
            right = spec.get("right") or {}
            cat.slot(left.get("slot", ""))
            if "attr" not in left:
                raise CatalogError(f"{where}: left needs attr")
            if "value" in right:
                to_fraction(right["value"], where + ".right.value")
            else:
                cat.slot(right.get("slot", ""))
                if "attr" not in right:
                    raise CatalogError(f"{where}: right needs attr or value")
            if spec.get("op") not in OPS:
                raise CatalogError(f"{where}: bad op {spec.get('op')!r}")
            to_fraction(spec.get("factor", 1), where + ".factor")
            to_fraction(spec.get("offset", 0), where + ".offset")
            if spec.get("missing", "fail") not in ("fail", "ignore"):
                raise CatalogError(f"{where}: missing must be 'fail' or 'ignore'")
        elif rtype == "sum":
            if not spec.get("slots") or "attr" not in spec:
                raise CatalogError(f"{where}: sum needs slots and attr")
            for sid in spec["slots"]:
                cat.slot(sid)
            if spec.get("op") not in OPS or spec.get("op") in ("!=",):
                raise CatalogError(f"{where}: bad op {spec.get('op')!r}")
            if "value" in spec:
                to_fraction(spec["value"], where + ".value")
            else:
                b = spec.get("bound") or {}
                cat.slot(b.get("slot", ""))
                if "attr" not in b:
                    raise CatalogError(f"{where}: needs value or bound.attr")
                to_fraction(spec.get("factor", 1), where + ".factor")
        cat.rules.append(Rule(id=rid, type=rtype, label=str(r.get("label") or rid), spec=spec))
    return cat
