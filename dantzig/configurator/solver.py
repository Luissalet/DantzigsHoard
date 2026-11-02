"""CP-SAT model of a catalog and the configurator operations.

Every operation returns plain JSON-able dicts. Statuses:

``optimal``       proven best for the requested objective
``feasible``      valid, but optimality not proven within the time limit
``infeasible``    proven impossible
``inconclusive``  the time limit ran out before an answer
"""
from __future__ import annotations

from fractions import Fraction
from math import lcm
from time import monotonic
from typing import Any, Iterable

from ortools.sat.python import cp_model

from .catalog import NONE, Catalog, CatalogError, to_fraction
from .rules import Assignment, compare_pair, selector_values, violations

DEFAULT_TIME_LIMIT = 10.0
_STATUS = {
    cp_model.OPTIMAL: "optimal",
    cp_model.FEASIBLE: "feasible",
    cp_model.INFEASIBLE: "infeasible",
    cp_model.UNKNOWN: "inconclusive",
    cp_model.MODEL_INVALID: "inconclusive",
}


def _scale(values: Iterable[Fraction]) -> int:
    k = 1
    for v in values:
        k = lcm(k, v.denominator)
    return k


def _numeric(v: Any) -> Fraction | None:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float, Fraction)):
        return to_fraction(v, "attr")
    return None


def _linear(expr: Any, op: str, rhs: Any) -> Any:
    if op == "<":
        return expr < rhs
    if op == "<=":
        return expr <= rhs
    if op == "==":
        return expr == rhs
    if op == "!=":
        return expr != rhs
    if op == ">=":
        return expr >= rhs
    if op == ">":
        return expr > rhs
    raise CatalogError(f"bad operator {op!r}")


def normalize_selections(cat: Catalog, selections: dict[str, Any] | None) -> Assignment:
    """Validate user selections ({slot: option id or None})."""
    out: Assignment = {}
    for sid, val in (selections or {}).items():
        slot = cat.slot(sid)
        if val in (None, "", "__none__"):
            if slot.required:
                raise CatalogError(f"slot {sid!r} is required and cannot be left empty")
            out[sid] = NONE
        else:
            slot.option(str(val))
            out[sid] = str(val)
    return out


class ConfigModel:
    """CP-SAT encoding with one enforcement literal per rule, stock line and selection."""

    def __init__(self, cat: Catalog, seconds: float = DEFAULT_TIME_LIMIT):
        self.cat = cat
        self.deadline = monotonic() + float(seconds)
        self.m = cp_model.CpModel()
        self.x: dict[tuple[str, str | None], cp_model.IntVar] = {}
        for slot in cat.slots:
            lits = []
            for v in slot.values():
                var = self.m.NewBoolVar(f"x[{slot.id}={v}]")
                self.x[(slot.id, v)] = var
                lits.append(var)
            self.m.AddExactlyOne(lits)
        # enforcement literals: rule id / __stock__:slot:opt -> literal
        self.guards: dict[str, cp_model.IntVar] = {}
        for slot in cat.slots:
            for o in slot.options:
                if cat.stock_policy == "strict" and not o.available():
                    g = self.m.NewBoolVar(f"__stock__:{slot.id}:{o.id}")
                    self.guards[f"__stock__:{slot.id}:{o.id}"] = g
                    self.m.Add(self.x[(slot.id, o.id)] == 0).OnlyEnforceIf(g)
        for rule in cat.rules:
            g = self.m.NewBoolVar(rule.id)
            self.guards[rule.id] = g
            getattr(self, f"_enc_{rule.type}")(rule, g)
        self.sel: dict[tuple[str, str | None], cp_model.IntVar] = {}

    # -- encodings ---------------------------------------------------------
    def _lits(self, sel: dict[str, Any]) -> list[cp_model.IntVar]:
        return [self.x[(sel["slot"], v)] for v in selector_values(self.cat, sel)]

    def _enc_requires(self, rule, g) -> None:
        a = self._lits(rule.spec["if"])
        b = self._lits(rule.spec["then"])
        for xa in a:
            if b:
                self.m.AddBoolOr(b).OnlyEnforceIf([xa, g])
            else:
                self.m.Add(xa == 0).OnlyEnforceIf(g)

    def _enc_excludes(self, rule, g) -> None:
        a = self._lits(rule.spec["a"])
        b = self._lits(rule.spec["b"])
        for xa in a:
            for xb in b:
                if xa is xb:
                    self.m.Add(xa == 0).OnlyEnforceIf(g)
                else:
                    self.m.AddBoolOr([xa.Not(), xb.Not()]).OnlyEnforceIf(g)

    def _enc_compare(self, rule, g) -> None:
        spec = rule.spec
        ls = self.cat.slot(spec["left"]["slot"])
        if "value" in spec["right"]:
            for lv in ls.values():
                if not compare_pair(self.cat, rule, lv, NONE):
                    self.m.Add(self.x[(ls.id, lv)] == 0).OnlyEnforceIf(g)
            return
        rs = self.cat.slot(spec["right"]["slot"])
        for lv in ls.values():
            for rv in rs.values():
                if ls.id == rs.id and lv != rv:
                    continue
                if compare_pair(self.cat, rule, lv, rv):
                    continue
                xl, xr = self.x[(ls.id, lv)], self.x[(rs.id, rv)]
                if xl is xr:
                    self.m.Add(xl == 0).OnlyEnforceIf(g)
                else:
                    self.m.AddBoolOr([xl.Not(), xr.Not()]).OnlyEnforceIf(g)

    def _enc_sum(self, rule, g) -> None:
        spec = rule.spec
        terms: list[tuple[Fraction, Any]] = []
        for sid in spec["slots"]:
            for o in self.cat.slot(sid).options:
                c = _numeric(o.attrs.get(spec["attr"]))
                if c:
                    terms.append((c, self.x[(sid, o.id)]))
        if "value" in spec:
            bound = to_fraction(spec["value"], "value")
            k = _scale([c for c, _ in terms] + [bound])
            expr = sum(int(c * k) * v for c, v in terms) if terms else 0
            self.m.Add(_linear(expr, spec["op"], int(bound * k))).OnlyEnforceIf(g)
            return
        b = spec["bound"]
        factor = to_fraction(spec.get("factor", 1), "factor")
        bterms = []
        for o in self.cat.slot(b["slot"]).options:
            c = _numeric(o.attrs.get(b["attr"]))
            if c:
                bterms.append((c * factor, self.x[(b["slot"], o.id)]))
        k = _scale([c for c, _ in terms] + [c for c, _ in bterms])
        lhs = sum(int(c * k) * v for c, v in terms) if terms else 0
        rhs = sum(int(c * k) * v for c, v in bterms) if bterms else 0
        self.m.Add(_linear(lhs - rhs, spec["op"], 0)).OnlyEnforceIf(g)

    # -- selections --------------------------------------------------------
    def selection_literal(self, sid: str, val: str | None) -> cp_model.IntVar:
        key = (sid, val)
        if key not in self.sel:
            lit = self.m.NewBoolVar(f"sel[{sid}={val}]")
            self.m.Add(self.x[key] == 1).OnlyEnforceIf(lit)
            self.sel[key] = lit
        return self.sel[key]

    # -- solving -----------------------------------------------------------
    def remaining(self) -> float:
        return max(0.0, self.deadline - monotonic())

    def solve(self, assumptions: list, *, cap: float | None = None, workers: int = 1):
        """Solve within the operation's remaining budget (optionally capped for this step).

        Returns ``(None, UNKNOWN)`` without solving once the budget is spent.
        """
        rem = self.remaining()
        time_limit = rem if cap is None else min(rem, cap)
        if time_limit <= 0.001:
            return None, cp_model.UNKNOWN
        self.m.ClearAssumptions()
        if assumptions:
            self.m.AddAssumptions(assumptions)
        s = cp_model.CpSolver()
        s.parameters.max_time_in_seconds = float(time_limit)
        s.parameters.num_workers = workers
        s.parameters.random_seed = 0
        st = s.Solve(self.m)
        return s, st

    def assignment(self, s: cp_model.CpSolver) -> Assignment:
        out: Assignment = {}
        for slot in self.cat.slots:
            for v in slot.values():
                if s.Value(self.x[(slot.id, v)]):
                    out[slot.id] = v
        return out

    def objective_expr(self, term: dict[str, Any]):
        attr = term.get("attr", "price")
        coefs: list[tuple[Fraction, Any]] = []
        for slot in self.cat.slots:
            for o in slot.options:
                if attr == "price":
                    c: Fraction | None = o.price * o.qty
                elif attr == "count":
                    c = Fraction(1)
                else:
                    c = _numeric(o.attrs.get(attr))
                if c:
                    coefs.append((c, self.x[(slot.id, o.id)]))
        k = _scale(c for c, _ in coefs)
        expr = sum(int(c * k) * v for c, v in coefs) if coefs else 0
        return expr, k


def _all_guards(model: ConfigModel) -> list:
    return list(model.guards.values())


def bom(cat: Catalog, asg: Assignment) -> dict[str, Any]:
    lines = []
    total = Fraction(0)
    for slot in cat.slots:
        v = asg.get(slot.id, NONE)
        if v is NONE:
            continue
        o = slot.option(v)
        line_total = o.price * o.qty
        total += line_total
        lines.append(
            {
                "slot": slot.id,
                "slot_label": slot.label,
                "option": o.id,
                "label": o.label,
                "qty": o.qty,
                "unit_price": _out(o.price),
                "total": _out(line_total),
                "stock": o.stock,
                "available": o.available(),
                "attrs": o.attrs,
            }
        )
    return {"currency": cat.currency, "lines": lines, "total": _out(total)}


def _out(x: Fraction) -> int | float | str:
    from .catalog import exact_number

    return exact_number(x)


def _explain_label(cat: Catalog, key: str) -> dict[str, Any]:
    if key.startswith("__stock__:"):
        _, sid, oid = key.split(":", 2)
        o = cat.slot(sid).option(oid)
        return {"id": key, "kind": "stock", "label": f"Sin existencias: {o.label} ({o.stock} disponibles, necesita {o.qty})"}
    r = cat.rule(key)
    return {"id": r.id, "kind": "rule", "type": r.type, "label": r.label}


def check(cat: Catalog, selections: dict[str, Any] | None = None, *, time_limit: float = DEFAULT_TIME_LIMIT) -> dict[str, Any]:
    """Is there any valid configuration that keeps all selections?"""
    sel = normalize_selections(cat, selections)
    model = ConfigModel(cat, time_limit)
    lits = [model.selection_literal(k, v) for k, v in sel.items()]
    s, st = model.solve(lits + _all_guards(model))
    status = _STATUS[st]
    out: dict[str, Any] = {"status": "feasible" if status in ("optimal", "feasible") else status, "selections": sel}
    if status in ("optimal", "feasible"):
        asg = model.assignment(s)
        out["example"] = asg
        out["violations"] = violations(cat, asg)
    return out


def _mus(model: ConfigModel, fixed: list, items: list) -> tuple[list, bool]:
    """Deletion-based minimal subset of ``items`` that stays infeasible with ``fixed``."""
    keep = list(items)
    complete = True
    i = 0
    while i < len(keep):
        trial = keep[:i] + keep[i + 1 :]
        _, st = model.solve(fixed + trial)
        if st == cp_model.INFEASIBLE:
            keep = trial
        else:
            if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                complete = False
            i += 1
    return keep, complete


def explain(cat: Catalog, selections: dict[str, Any] | None = None, *, time_limit: float = DEFAULT_TIME_LIMIT, max_conflicts: int = 6) -> dict[str, Any]:
    """Minimal conflicting selection sets and, for each, the minimal rules that make them clash.

    ``conflict`` is the first one found; ``conflicts`` lists up to ``max_conflicts``
    distinct minimal conflicts (``exhaustive`` says whether there can be more).
    """
    sel = normalize_selections(cat, selections)
    model = ConfigModel(cat, time_limit)
    sel_key = {model.selection_literal(k, v).Index(): (k, v) for k, v in sel.items()}
    guard_by_idx = {g.Index(): name for name, g in model.guards.items()}
    sl = [model.sel[(k, v)] for k, v in sel.items()]
    gl = _all_guards(model)
    _, st = model.solve(sl + gl)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "feasible", "selections": sel, "conflict": None, "conflicts": []}
    if st != cp_model.INFEASIBLE:
        return {"status": "inconclusive", "selections": sel, "conflict": None, "conflicts": []}
    minimal = True
    found: list[frozenset[int]] = []
    conflicts: list[dict[str, Any]] = []
    queue: list[list] = [sl]
    seen: set[frozenset[int]] = set()
    exhaustive = True
    while queue:
        subset = queue.pop(0)
        key = frozenset(l.Index() for l in subset)
        if key in seen:
            continue
        seen.add(key)
        if any(f <= key for f in found):
            core = next(f for f in found if f <= key)
            core_lits = [l for l in subset if l.Index() in core]
        else:
            _, st = model.solve(subset + gl)
            if st != cp_model.INFEASIBLE:
                if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                    exhaustive = False
                continue
            core_lits, ok1 = _mus(model, gl, subset)
            rule_core, ok2 = _mus(model, core_lits, gl)
            minimal = minimal and ok1 and ok2
            found.append(frozenset(l.Index() for l in core_lits))
            conflicts.append(
                {
                    "selections": [{"slot": sel_key[l.Index()][0], "option": sel_key[l.Index()][1]} for l in core_lits],
                    "rules": [_explain_label(cat, guard_by_idx[g.Index()]) for g in rule_core],
                }
            )
            if len(conflicts) >= max_conflicts:
                exhaustive = False
                break
        for lit in core_lits:
            queue.append([l for l in subset if l is not lit])
    return {
        "status": "infeasible",
        "selections": sel,
        "minimal": minimal,
        "exhaustive": exhaustive,
        "conflict": conflicts[0] if conflicts else None,
        "conflicts": conflicts,
    }


def propagate(cat: Catalog, selections: dict[str, Any] | None = None, *, time_limit: float = DEFAULT_TIME_LIMIT) -> dict[str, Any]:
    """For each slot, which values remain possible when the *other* selections are kept."""
    sel = normalize_selections(cat, selections)
    model = ConfigModel(cat, time_limit)
    gl = _all_guards(model)
    left = sum(len(s.values()) for s in cat.slots) + 1
    slots_out = []
    inconclusive = False
    for slot in cat.slots:
        others = [model.selection_literal(k, v) for k, v in sel.items() if k != slot.id]
        viable, removed = [], []
        for v in slot.values():
            _, st = model.solve(others + gl + [model.selection_literal(slot.id, v)], cap=model.remaining() / left)
            left -= 1
            if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                viable.append(v)
            elif st == cp_model.INFEASIBLE:
                removed.append(v)
            else:
                inconclusive = True
                viable.append(v)
        slots_out.append(
            {
                "slot": slot.id,
                "label": slot.label,
                "required": slot.required,
                "selected": sel.get(slot.id),
                "is_set": slot.id in sel,
                "viable": viable,
                "removed": removed,
                "forced": viable[0] if len(viable) == 1 else None,
                "selection_ok": (sel[slot.id] in viable) if slot.id in sel else None,
            }
        )
    _, st = model.solve([model.selection_literal(k, v) for k, v in sel.items()] + gl)
    feasible_now = st in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE):
        inconclusive = True
    return {"status": "inconclusive" if inconclusive else "ok", "consistent": feasible_now, "slots": slots_out}


def _optimize(model: ConfigModel, base_assumptions: list, objective: list[dict[str, Any]], prefix: list[tuple[Any, int, str]]):
    """Lexicographic optimisation in stages within the model's budget.

    Each stage minimises one term with the earlier optima fixed. A stage only
    fixes a *proven* optimum; if a later stage runs out of time the best
    assignment found so far is returned as ``feasible``.
    """
    terms: list[tuple[Any, int, str]] = list(prefix)
    for t in objective or [{"attr": "price", "sense": "min"}]:
        expr, _ = model.objective_expr(t)
        terms.append((expr, 1 if t.get("sense", "min") == "min" else -1, t.get("attr", "price")))
    best: Assignment | None = None
    values: list[int] = []
    for n, (expr, sense, _label) in enumerate(terms):
        if isinstance(expr, int):  # constant term: nothing to optimise
            values.append(expr)
            continue
        if sense == 1:
            model.m.Minimize(expr)
        else:
            model.m.Maximize(expr)
        s, st = model.solve(base_assumptions, cap=model.remaining() / (len(terms) - n), workers=8)
        model.m.ClearObjective()
        if st == cp_model.INFEASIBLE and best is None:
            return "infeasible", None, values
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return ("feasible" if best is not None else "inconclusive"), best, values
        best = model.assignment(s)
        val = int(s.Value(expr))
        values.append(val)
        if st != cp_model.OPTIMAL:
            return "feasible", best, values
        model.m.Add(expr == val)
    if best is None:  # every term was constant
        s, st = model.solve(base_assumptions)
        if st == cp_model.INFEASIBLE:
            return "infeasible", None, values
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return "inconclusive", None, values
        best = model.assignment(s)
    return "optimal", best, values


def _clear_fix(model: ConfigModel, fixes: list) -> None:
    """Models are built per call, so fixed objective rows are simply left behind."""
    model.m.ClearObjective()


def complete(cat: Catalog, selections: dict[str, Any] | None = None, *, objective: list[dict[str, Any]] | None = None, time_limit: float = DEFAULT_TIME_LIMIT) -> dict[str, Any]:
    """Fill every unset slot keeping the selections, best by ``objective`` (lexicographic)."""
    sel = normalize_selections(cat, selections)
    model = ConfigModel(cat, time_limit)
    lits = [model.selection_literal(k, v) for k, v in sel.items()]
    status, asg, values = _optimize(model, lits + _all_guards(model), objective or [], [])
    out: dict[str, Any] = {"status": status, "selections": sel, "objective": objective or [{"attr": "price", "sense": "min"}]}
    if asg is not None:
        out["configuration"] = asg
        out["filled"] = {k: v for k, v in asg.items() if k not in sel}
        out["bom"] = bom(cat, asg)
        out["violations"] = violations(cat, asg)
    elif status == "infeasible":
        out["conflict"] = explain(cat, sel, time_limit=max(model.remaining(), 0.001)).get("conflict")
    return out


def repair(cat: Catalog, selections: dict[str, Any] | None = None, *, objective: list[dict[str, Any]] | None = None, time_limit: float = DEFAULT_TIME_LIMIT) -> dict[str, Any]:
    """Keep as many selections as possible; change the fewest, then optimise ``objective``."""
    sel = normalize_selections(cat, selections)
    model = ConfigModel(cat, time_limit)
    lits = [model.selection_literal(k, v) for k, v in sel.items()]
    broken = sum(1 - l for l in lits) if lits else 0
    status, asg, values = _optimize(model, _all_guards(model), objective or [], [(broken, 1, "changes")])
    out: dict[str, Any] = {"status": status, "selections": sel}
    if asg is None:
        if status == "infeasible":
            out["conflict"] = explain(cat, {}, time_limit=max(model.remaining(), 0.001)).get("conflict")
            out["reason"] = "El catálogo no admite ninguna configuración válida."
        return out
    changes = [{"slot": k, "from": v, "to": asg.get(k)} for k, v in sel.items() if asg.get(k) != v]
    out.update(
        {
            "configuration": asg,
            "changes": changes,
            "kept": {k: v for k, v in sel.items() if asg.get(k) == v},
            "change_count": len(changes),
            "bom": bom(cat, asg),
            "violations": violations(cat, asg),
        }
    )
    if changes:
        ex = explain(cat, sel, time_limit=max(model.remaining(), 0.001))
        out["original_conflict"] = ex.get("conflict")
        out["original_conflicts"] = ex.get("conflicts")
    return out
