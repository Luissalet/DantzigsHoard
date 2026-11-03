"""Calendar constraints checked against independent integer-time enumeration."""
import itertools
import json
import os
import random
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from dantzig.app import app
from dantzig.models import Problem
from dantzig.solver import solve, verify


def problem(**changes):
    return Problem.model_validate({"name": "Calendar example", "resources": ["M"],
        "jobs": [{"id": "A", "durations": {"M": 12}}],
        "unavailability": {"M": [{"start": 10, "end": 20}]}, **changes})


def test_job_cannot_cross_a_closure_and_automatic_horizon_is_sufficient():
    p = problem()
    result = solve(p)
    assert result["status"] == "optimal" and result["horizon"] == 32
    assert result["schedule"] == [{"job": "A", "resource": "M", "start": 20, "end": 32}]
    assert verify(p, [{"job": "A", "resource": "M", "start": 0, "end": 12}])


def test_overlapping_touching_and_unsorted_windows_are_a_union():
    p = problem(jobs=[{"id": "A", "durations": {"M": 2}}],
        unavailability={"M": [{"start":3,"end":6},{"start":1,"end":4},{"start":6,"end":7}]})
    result = solve(p)
    assert result["status"] == "optimal" and result["makespan"] == 9
    assert len(p.unavailability["M"]) == 3  # original input is retained


def test_horizon_clips_windows_without_allowing_work_in_the_closed_part():
    assert solve(problem(horizon=5, unavailability={"M":[{"start":0,"end":100}]}))["status"] == "infeasible"
    r = solve(problem(horizon=12, unavailability={"M":[{"start":100,"end":110}]}))
    assert r["status"] == "optimal" and r["makespan"] == 12


def test_half_open_boundaries_and_family_gap_can_elapse_during_a_closure():
    p = problem(jobs=[{"id":"A","durations":{"M":2},"family":"x"},
                      {"id":"B","durations":{"M":2},"family":"y","after":["A"]}],
        unavailability={"M":[{"start":2,"end":5}]}, family_change=3)
    r = solve(p)
    assert r["status"] == "optimal" and r["makespan"] == 7
    assert [(x["start"],x["end"]) for x in r["schedule"]] == [(0,2),(5,7)]


def test_an_alternative_resource_can_avoid_a_closed_machine():
    p = problem(resources=["M","N"], jobs=[{"id":"A","durations":{"M":1,"N":4}}],
        unavailability={"M":[{"start":0,"end":10}]})
    r = solve(p)
    assert r["makespan"] == 4 and r["schedule"][0]["resource"] == "N"


@pytest.mark.parametrize("window", [{"start":0,"end":0},{"start":3,"end":2},
    {"start":-1,"end":2},{"start":True,"end":2},{"start":0,"end":2.5}])
def test_invalid_windows_are_explicit(window):
    with pytest.raises(ValidationError):
        problem(unavailability={"M":[window]})


def test_unknown_resource_and_old_documents():
    with pytest.raises(ValidationError,match="desconocido"):
        problem(unavailability={"unknown":[{"start":0,"end":1}]})
    p = Problem.model_validate({"name":"Old", "resources":["M"], "jobs":[{"id":"A","durations":{"M":2}}]})
    assert p.unavailability == {} and solve(p)["makespan"] == 2


def enumerate_optimum(p):
    """Enumerate starts directly, without circuits, merged calendars or CP-SAT."""
    choices = []
    for j in p.jobs:
        possible = []
        for resource, duration in j.durations.items():
            for start in range(j.release, p.horizon - duration + 1):
                end = start + duration
                if j.deadline is not None and end > j.deadline:
                    continue
                if any(start < w.end and end > w.start for w in p.unavailability.get(resource, [])):
                    continue
                possible.append((resource,start,end))
        choices.append(possible)
    best = None
    for rows in itertools.product(*choices):
        ends = {j.id:r[2] for j,r in zip(p.jobs,rows)}
        if any(ends[parent] > row[1] for j,row in zip(p.jobs,rows) for parent in j.after):
            continue
        valid = True
        for i,j in itertools.combinations(range(len(rows)),2):
            if rows[i][0] != rows[j][0]:
                continue
            left,right = sorted((i,j),key=lambda k:rows[k][1])
            gap = p.family_change if p.jobs[left].family != p.jobs[right].family else 0
            if rows[right][1] < rows[left][2] + gap:
                valid = False
                break
        if not valid:
            continue
        late = sum(j.weight * max(0,r[2]-j.due) for j,r in zip(p.jobs,rows) if j.due is not None)
        span = max(r[2] for r in rows)
        value = (late,span) if p.objective == "tardiness_then_makespan" else (span,late)
        if best is None or value < best:
            best = value
    return best


@pytest.mark.parametrize("seed", range(12))
def test_calendar_solutions_match_independent_exhaustive_search(seed):
    rng = random.Random(seed)
    raw = {"name":f"Oracle {seed}","resources":["M","N"],"horizon":10,
        "jobs":[{"id":str(i),"durations":{r:rng.randint(1,3) for r in ("M","N")},
                 "release":rng.randint(0,2),"due":rng.randint(2,8),"family":str(i%2),
                 "weight":rng.randint(1,3),"after":["0"] if i==2 and seed%2 else []} for i in range(3)],
        "family_change":seed%2,
        "unavailability":{r:[{"start":a,"end":a+rng.randint(1,3)} for a in (2,4)] for r in ("M","N")}}
    if seed % 3 == 0:
        raw["jobs"][2]["deadline"] = 6
    for objective in ("tardiness_then_makespan","makespan_then_tardiness"):
        p = Problem.model_validate({**raw,"objective":objective})
        expected = enumerate_optimum(p)
        actual = solve(p,seconds=5)
        if expected is None:
            assert actual["status"] == "infeasible"
        else:
            assert actual["status"] == "optimal"
            value = (actual["weighted_tardiness"],actual["makespan"]) if objective.startswith("tardiness") else (actual["makespan"],actual["weighted_tardiness"])
            assert value == expected


def test_http_roundtrip_keeps_original_calendar_and_returns_calendar_plan(tmp_path,monkeypatch):
    monkeypatch.setenv('DANTZIG_DATA',str(tmp_path))
    p = problem().model_dump()
    with TestClient(app) as client:
        saved = client.post('/api/problems',json=p).json()
        assert client.get('/api/records/'+saved['id']).json()['unavailability'] == p['unavailability']
        result = client.post('/api/solve',json={'problem':p,'seconds':5})
        assert result.status_code == 200 and result.json()['result']['makespan'] == 32
        assert result.json()['problem']['unavailability'] == p['unavailability']


@pytest.fixture
def anyio_backend(): return 'asyncio'


@pytest.mark.anyio
async def test_calendar_problem_through_real_mcp(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=sys.executable,args=['-m','dantzig.mcp_server'],
        env={**os.environ,'DANTZIG_DATA':str(tmp_path/'mcp')})
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            await session.list_tools()
            assert not (tmp_path/'mcp').exists()
            result = await session.call_tool('dantzig_solve',{'problem':problem().model_dump(),'seconds':5})
            assert not result.is_error
            data = json.loads(next(x.text for x in result.content if x.type=='text'))
            assert data['result']['status'] == 'optimal' and data['result']['makespan'] == 32
            assert data['problem']['unavailability']['M'] == [{'start':10,'end':20}]
