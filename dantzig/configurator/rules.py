"""Direct (solver-free) evaluation of catalog rules on a full assignment.

This is the semantic reference: the verifier uses it to check any
configuration returned by the CP-SAT model.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

from .catalog import NONE, Catalog, CatalogError, Rule, to_fraction

Assignment = dict[str, "str | None"]


def compare(a: Any, op: str, b: Any) -> bool:
    if op == "<":
        return a < b
    if op == "<=":
        return a <= b
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    if op == ">=":
        return a >= b
    if op == ">":
        return a > b
    raise CatalogError(f"bad operator {op!r}")


def _num_or_raw(v: Any) -> Any:
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float, Fraction)):
        return to_fraction(v, "attr")
    return v


def attr_value(cat: Catalog, slot: str, value: str | None, attr: str) -> Any:
    """Attribute of the chosen option, ``None`` when empty or missing."""
    if value is NONE:
        return None
    return _num_or_raw(cat.slot(slot).option(value).attrs.get(attr))


def selector_values(cat: Catalog, sel: dict[str, Any]) -> set[str | None]:
    """The set of slot values (option ids or NONE) a selector accepts."""
    slot = cat.slot(sel["slot"])
    if "option" in sel:
        return {sel["option"]}
    if "options" in sel:
        return set(sel["options"])
    if "chosen" in sel:
        return {o.id for o in slot.options} if sel["chosen"] else {NONE}
    want = _num_or_raw(sel["value"])
    out: set[str | None] = set()
    for o in slot.options:
        have = _num_or_raw(o.attrs.get(sel["attr"]))
        if have is None:
            continue
        try:
            if compare(have, sel["op"], want):
                out.add(o.id)
        except TypeError:
            continue
    return out


def selector_holds(cat: Catalog, sel: dict[str, Any], asg: Assignment) -> bool:
    return asg.get(sel["slot"]) in selector_values(cat, sel)


def compare_pair(cat: Catalog, rule: Rule, lv: str | None, rv: str | None) -> bool:
    """Evaluate a ``compare`` rule for given left/right slot values."""
    spec = rule.spec
    left, right = spec["left"], spec["right"]
    if lv is NONE:
        return True
    a = attr_value(cat, left["slot"], lv, left["attr"])
    if "value" in right:
        b: Any = to_fraction(right["value"], "value")
    else:
        if rv is NONE:
            return True
        b = attr_value(cat, right["slot"], rv, right["attr"])
    if a is None or b is None:
        return spec.get("missing", "fail") == "ignore"
    fail_ok = spec.get("missing", "fail") == "ignore"
    if isinstance(b, Fraction):
        if not isinstance(a, Fraction):
            return fail_ok
        b = b * to_fraction(spec.get("factor", 1), "factor") + to_fraction(spec.get("offset", 0), "offset")
        return compare(a, spec["op"], b)
    if isinstance(a, Fraction) or type(a) is not type(b):
        return fail_ok
    if spec["op"] in ("==", "!="):
        return compare(a, spec["op"], b)
    try:
        return compare(a, spec["op"], b)
    except TypeError:
        return fail_ok


def sum_terms(cat: Catalog, rule: Rule, asg: Assignment) -> tuple[Fraction, Fraction]:
    spec = rule.spec
    total = Fraction(0)
    for sid in spec["slots"]:
        v = attr_value(cat, sid, asg.get(sid), spec["attr"])
        if isinstance(v, Fraction):
            total += v
    if "value" in spec:
        bound = to_fraction(spec["value"], "value")
    else:
        b = spec["bound"]
        bv = attr_value(cat, b["slot"], asg.get(b["slot"]), b["attr"])
        bound = (bv if isinstance(bv, Fraction) else Fraction(0)) * to_fraction(spec.get("factor", 1), "factor")
    return total, bound


def rule_holds(cat: Catalog, rule: Rule, asg: Assignment) -> bool:
    spec = rule.spec
    if rule.type == "requires":
        return (not selector_holds(cat, spec["if"], asg)) or selector_holds(cat, spec["then"], asg)
    if rule.type == "excludes":
        return not (selector_holds(cat, spec["a"], asg) and selector_holds(cat, spec["b"], asg))
    if rule.type == "compare":
        rv = None if "value" in spec["right"] else asg.get(spec["right"]["slot"])
        return compare_pair(cat, rule, asg.get(spec["left"]["slot"]), rv)
    if rule.type == "sum":
        total, bound = sum_terms(cat, rule, asg)
        return compare(total, spec["op"], bound)
    raise CatalogError(f"unknown rule type {rule.type!r}")


def violations(cat: Catalog, asg: Assignment) -> list[str]:
    """Ids of everything a full assignment breaks (rules, stock, domains)."""
    out: list[str] = []
    for slot in cat.slots:
        v = asg.get(slot.id, NONE)
        if v is NONE:
            if slot.required:
                out.append(f"__required__:{slot.id}")
            continue
        try:
            opt = slot.option(v)
        except CatalogError:
            out.append(f"__unknown__:{slot.id}")
            continue
        if cat.stock_policy == "strict" and not opt.available():
            out.append(f"__stock__:{slot.id}:{v}")
    if out and any(x.startswith("__unknown__") for x in out):
        return out
    for rule in cat.rules:
        if not rule_holds(cat, rule, asg):
            out.append(rule.id)
    return out
