"""Independent reference: brute-force enumeration without the solver.

Only usable on small catalogs; used by tests and by the ``verify`` endpoint to
cross-check what CP-SAT returns.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import product
from typing import Any, Iterator

from .catalog import NONE, Catalog, CatalogError
from .rules import Assignment, violations
from .solver import _numeric

MAX_ENUMERATION = 250_000


def space_size(cat: Catalog) -> int:
    n = 1
    for s in cat.slots:
        n *= len(s.values())
    return n


def enumerate_valid(cat: Catalog, fixed: Assignment | None = None, *, limit: int = MAX_ENUMERATION) -> Iterator[Assignment]:
    fixed = fixed or {}
    if space_size(cat) > limit:
        raise CatalogError(f"search space {space_size(cat)} exceeds enumeration limit {limit}")
    domains = [[fixed[s.id]] if s.id in fixed else s.values() for s in cat.slots]
    ids = cat.slot_ids()
    for combo in product(*domains):
        asg = dict(zip(ids, combo))
        if not violations(cat, asg):
            yield asg


def objective_value(cat: Catalog, asg: Assignment, term: dict[str, Any]) -> Fraction:
    attr = term.get("attr", "price")
    total = Fraction(0)
    for s in cat.slots:
        v = asg.get(s.id, NONE)
        if v is NONE:
            continue
        o = s.option(v)
        if attr == "price":
            total += o.price * o.qty
        elif attr == "count":
            total += 1
        else:
            c = _numeric(o.attrs.get(attr))
            total += c or 0
    return total if term.get("sense", "min") == "min" else -total


def key(cat: Catalog, asg: Assignment, objective: list[dict[str, Any]], selections: Assignment | None = None) -> tuple:
    parts: list[Fraction] = []
    if selections is not None:
        parts.append(Fraction(sum(1 for k, v in selections.items() if asg.get(k) != v)))
    for t in objective or [{"attr": "price", "sense": "min"}]:
        parts.append(objective_value(cat, asg, t))
    return tuple(parts)


def best_completion(cat: Catalog, selections: Assignment, objective: list[dict[str, Any]] | None = None) -> tuple | None:
    best = None
    for asg in enumerate_valid(cat, selections):
        k = key(cat, asg, objective or [])
        if best is None or k < best:
            best = k
    return best


def best_repair(cat: Catalog, selections: Assignment, objective: list[dict[str, Any]] | None = None) -> tuple | None:
    best = None
    for asg in enumerate_valid(cat):
        k = key(cat, asg, objective or [], selections)
        if best is None or k < best:
            best = k
    return best


def verify_result(cat: Catalog, result: dict[str, Any], mode: str, objective: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Check a ``complete``/``repair`` result against enumeration."""
    sel: Assignment = result.get("selections") or {}
    ref = best_completion(cat, sel, objective) if mode == "complete" else best_repair(cat, sel, objective)
    report: dict[str, Any] = {"mode": mode, "space": space_size(cat)}
    if ref is None:
        report["reference"] = "infeasible"
        report["agrees"] = result.get("status") == "infeasible"
        return report
    report["reference"] = "feasible"
    asg = result.get("configuration")
    if asg is None:
        report["agrees"] = False
        return report
    got = key(cat, asg, objective or [], sel if mode == "repair" else None)
    report["violations"] = violations(cat, asg)
    report["agrees"] = not report["violations"] and (got == ref if result.get("status") == "optimal" else got >= ref)
    report["reference_key"] = [float(x) for x in ref]
    report["result_key"] = [float(x) for x in got]
    return report
