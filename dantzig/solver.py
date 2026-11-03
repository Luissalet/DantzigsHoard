"""Owned scheduling model, backed by the in-process CP-SAT library.

Time is integral, jobs cannot be interrupted, resources have unit capacity.
Changeovers represent minimum elapsed gaps, not occupied setup operations.
"""
from ortools.sat.python import cp_model
from time import perf_counter
from math import floor, isfinite, nextafter, inf
from .models import Problem


class VerificationError(RuntimeError):
    pass


def integer_bound(solver):
    value = solver.best_objective_bound
    # Bounds arrive as doubles; one downward ULP avoids claiming a stronger
    # bound through conversion noise. Both objectives are nonnegative integers.
    return max(0, floor(nextafter(value, -inf))) if isfinite(value) else None


def verify(problem: Problem, rows: list[dict]) -> list[str]:
    """Check a candidate independently of CP-SAT and its objective expression."""
    errors = []
    by_id = {r["job"]: r for r in rows}
    if len(by_id) != len(rows) or set(by_id) != {j.id for j in problem.jobs}:
        return ["Cada trabajo debe aparecer exactamente una vez"]
    jobs = {j.id: j for j in problem.jobs}
    for key, row in by_id.items():
        j = jobs[key]
        if row["resource"] not in j.durations:
            errors.append(f"{key}: recurso incompatible")
            continue
        if row["end"] - row["start"] != j.durations[row["resource"]]:
            errors.append(f"{key}: duración incorrecta")
        if row["start"] < j.release:
            errors.append(f"{key}: empieza antes de estar disponible")
        if j.deadline is not None and row["end"] > j.deadline:
            errors.append(f"{key}: incumple fecha límite obligatoria")
        if problem.horizon is not None and row["end"] > problem.horizon:
            errors.append(f"{key}: supera el horizonte")
        for parent in j.after:
            if by_id[parent]["end"] > row["start"]:
                errors.append(f"{key}: incumple precedencia de {parent}")
    for resource in problem.resources:
        ordered = sorted((r for r in rows if r["resource"] == resource), key=lambda r: r["start"])
        for a, b in zip(ordered, ordered[1:]):
            gap = problem.family_change if jobs[a["job"]].family != jobs[b["job"]].family else 0
            if b["start"] < a["end"] + gap:
                errors.append(f"{resource}: solapamiento o cambio de familia insuficiente")
    return errors


def solve(problem: Problem, seconds: float = 10) -> dict:
    horizon = problem.horizon or (
        max(j.release for j in problem.jobs)
        + sum(max(j.durations.values()) for j in problem.jobs)
        + problem.family_change * (len(problem.jobs) - 1)
    )
    model = cp_model.CpModel()
    starts, ends, choices = {}, {}, {}
    for j in problem.jobs:
        starts[j.id] = model.new_int_var(0, horizon, f"start_{j.id}")
        ends[j.id] = model.new_int_var(0, horizon, f"end_{j.id}")
        model.add(starts[j.id] >= j.release)
        if j.deadline is not None:
            model.add(ends[j.id] <= j.deadline)
        selected = []
        for r in j.durations:
            choices[j.id, r] = model.new_bool_var(f"use_{j.id}_{r}")
            selected.append(choices[j.id, r])
        model.add_exactly_one(selected)
    for j in problem.jobs:
        for parent in j.after:
            model.add(starts[j.id] >= ends[parent])
    for r in problem.resources:
        eligible = [j for j in problem.jobs if r in j.durations]
        intervals, arcs = [], []
        empty = model.new_bool_var(f"empty_{r}")
        arcs.append((0, 0, empty))
        uses = [choices[j.id, r] for j in eligible]
        model.add(sum(uses) == 0).only_enforce_if(empty)
        model.add(sum(uses) >= 1).only_enforce_if(empty.Not())
        for i, j in enumerate(eligible, 1):
            use = choices[j.id, r]
            intervals.append(model.new_optional_interval_var(starts[j.id], j.durations[r], ends[j.id], use, f"slot_{j.id}_{r}"))
            arcs.append((i, i, use.Not()))
            arcs.append((0, i, model.new_bool_var(f"first_{r}_{i}")))
            arcs.append((i, 0, model.new_bool_var(f"last_{r}_{i}")))
            for k, other in enumerate(eligible, 1):
                if i == k:
                    continue
                arc = model.new_bool_var(f"next_{r}_{i}_{k}")
                arcs.append((i, k, arc))
                gap = problem.family_change if j.family != other.family else 0
                model.add(starts[other.id] >= ends[j.id] + gap).only_enforce_if(arc)
        model.add_no_overlap(intervals)
        model.add_circuit(arcs)
    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, list(ends.values()))
    terms = []
    for j in problem.jobs:
        if j.due is not None:
            late = model.new_int_var(0, horizon, f"late_{j.id}")
            model.add_max_equality(late, [0, ends[j.id] - j.due])
            terms.append(j.weight * late)
    tardiness = sum(terms)
    primary, secondary = (tardiness, makespan) if problem.objective == "tardiness_then_makespan" else (makespan, tardiness)
    model.minimize(primary)
    error = model.validate()
    if error:
        raise ValueError(f"El modelo no es representable: {error}")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_workers = 1
    started = perf_counter()
    status = solver.solve(model)
    bounds = {"primary": integer_bound(solver), "secondary": None}
    if status == cp_model.OPTIMAL:
        # Fix only a proven primary optimum; never label a secondary optimum
        # under an unproven first-stage choice as globally lexicographic optimal.
        primary_value = solver.value(primary)
        bounds["primary"] = primary_value
        model.add(primary == primary_value)
        model.minimize(secondary)
        remaining = seconds - (perf_counter() - started)
        status = cp_model.FEASIBLE
        if remaining > 0:
            second = cp_model.CpSolver()
            second.parameters.max_time_in_seconds = remaining
            second.parameters.num_workers = 1
            second_status = second.solve(model)
            bounds["secondary"] = second.value(secondary) if second_status == cp_model.OPTIMAL else integer_bound(second)
            if second_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solver, status = second, second_status
        # Otherwise retain the first-stage incumbent and report feasible.
    result = {"status": solver.status_name(status).lower(), "objective": problem.objective,
              "unit": problem.unit, "horizon": horizon, "seconds": perf_counter() - started,
              "scope": "Trabajos indivisibles, recursos exclusivos, tiempos enteros; cambios de familia como separación mínima.",
              "schedule": []}
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result["message"] = "No existe un plan dentro de las condiciones y horizonte indicados" if status == cp_model.INFEASIBLE else "La búsqueda terminó sin determinar una solución"
        return result
    rows = [{"job": j.id, "resource": next(r for r in j.durations if solver.value(choices[j.id, r])),
             "start": solver.value(starts[j.id]), "end": solver.value(ends[j.id])} for j in problem.jobs]
    failures = verify(problem, rows)
    if failures:
        raise VerificationError(f"La comprobación independiente rechazó el plan: {failures}")
    result.update(schedule=rows, verified=True, makespan=max(r["end"] for r in rows),
                  weighted_tardiness=sum(j.weight * max(0, rows[i]["end"] - j.due) for i, j in enumerate(problem.jobs) if j.due is not None),
                  objective_bound=None, objective_bounds=bounds)
    return result
