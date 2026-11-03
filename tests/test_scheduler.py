import itertools
import json
import random
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from dantzig.models import Problem
from dantzig.solver import solve, verify
from dantzig.service import example
from dantzig.app import app


def exhaustive(p):
    best = None
    for order in itertools.permutations(p.jobs):
        for assignment in itertools.product(*(list(j.durations) for j in order)):
            finish = {r: 0 for r in p.resources}
            previous = {}
            late = 0
            for j, r in zip(order, assignment):
                gap = p.family_change if r in previous and previous[r] != j.family else 0
                end = max(j.release, finish[r] + gap) + j.durations[r]
                late += j.weight * max(0, end - j.due) if j.due is not None else 0
                finish[r], previous[r] = end, j.family
            value = (late, max(finish.values())) if p.objective=='tardiness_then_makespan' else (max(finish.values()),late)
            best = value if best is None else min(best, value)
    return best


def test_research_example():
    result = solve(Problem(**example()))
    assert result['status'] == 'optimal'
    assert (result['weighted_tardiness'], result['makespan']) == (4, 19)


@pytest.mark.parametrize('seed', range(12))
def test_against_independent_enumeration(seed):
    rng = random.Random(seed)
    p = Problem(name='inventado', resources=['r1','r2'], family_change=rng.randrange(4), jobs=[
        dict(id=str(i), durations={r:rng.randint(1,7) for r in ['r1','r2'] if r == 'r1' or rng.randrange(2)},
             family=str(rng.randrange(2)), release=rng.randrange(5), due=rng.randrange(4,15),weight=rng.randint(1,3)) for i in range(4)])
    for objective in ['tardiness_then_makespan','makespan_then_tardiness']:
        p.objective=objective
        r = solve(p)
        assert r['status'] == 'optimal'
        value=(r['weighted_tardiness'],r['makespan']) if objective=='tardiness_then_makespan' else (r['makespan'],r['weighted_tardiness'])
        assert value == exhaustive(p)


def test_deadlines_precedence_and_impossibility():
    p = Problem(name='cadena',resources=['r'],jobs=[dict(id='A',durations={'r':3}),dict(id='B',durations={'r':2},after=['A'],release=4,deadline=6)])
    r = solve(p)
    assert r['status'] == 'optimal'
    assert {x['job']:x for x in r['schedule']}['B']['start'] == 4
    p.jobs[1].deadline = 4
    assert solve(p)['status'] == 'infeasible'
    p.jobs[0].after = ['B']
    assert solve(p)['status'] == 'infeasible'


def test_reverse_objective_and_verifier():
    p = Problem(**example());p.objective='makespan_then_tardiness'
    r = solve(p)
    assert r['makespan'] <= 18
    r['schedule'][0]['start'] = -1
    assert verify(p,r['schedule'])


def test_large_horizon_avoids_lexicographic_scaling_overflow():
    p=Problem(name='escala grande',resources=['r'],horizon=3_000_000_000,
              jobs=[dict(id='A',durations={'r':2_000_000_000},due=1,weight=1000)])
    for objective in ['tardiness_then_makespan','makespan_then_tardiness']:
        p.objective=objective
        r=solve(p)
        assert r['status']=='optimal'
        assert r['makespan']==2_000_000_000
        assert r['weighted_tardiness']==1_999_999_999_000
        assert r['objective_bound'] is None
        assert r['objective_bounds']['secondary'] is not None
        assert all(isinstance(v,int) for v in r['objective_bounds'].values())


@pytest.mark.parametrize('mutate', [lambda p:p.update(extra=True), lambda p:p['jobs'][0]['durations'].update({'Máquina 1': True}), lambda p:p['jobs'][0].update(after=['missing']),lambda p:p['resources'].append(p['resources'][0])])
def test_reject_invalid_input(mutate):
    p = example();mutate(p)
    with pytest.raises(ValidationError):Problem(**p)


def test_http_persistence_reopen_and_export(tmp_path,monkeypatch):
    monkeypatch.setenv('DANTZIG_DATA',str(tmp_path))
    with TestClient(app) as c:
        p=c.get('/api/example').json()
        saved=c.post('/api/problems',json=p).json()
        run=c.post('/api/solve',json={'problem':p}).json()
        assert run['result']['verified']
        assert c.get('/api/records/'+run['id']).json()['problem']==p
        assert c.get('/api/records/'+saved['id']).json()['name']==p['name']
        assert len(c.get('/api/records').json())==2
        assert c.get('/api/records/missing').status_code==404
        assert c.post('/api/solve',json={'problem':p,'seconds':-1}).status_code==422
        assert c.post('/api/validate',json=p).json()==p
        p['jobs'][0]['after']=['B'];p['jobs'][1]['after']=['A']
        rejected=c.post('/api/validate',json=p)
        assert rejected.status_code==422 and 'cíclicas' in rejected.text
        assert c.get('/').status_code==200
        html=c.get('/').text
        assert 'data-hoard-app="dantzig"' in html
        assert html.index('/static/hoard-theme.css') < html.index('/static/planner.css')
        assert c.get('/static/app-icon.png').content.startswith(b'\x89PNG\r\n\x1a\n')
        assert c.get('/static/planner.js').status_code==200
        assert '/api/copilot/launcher.js' in c.get('/').text
        launcher=c.get('/api/copilot/launcher.js')
        assert launcher.status_code==200 and 'Faustus' in launcher.text
    with TestClient(app) as c:
        assert len(c.get('/api/records').json())==2


@pytest.mark.anyio
async def test_real_mcp_stdio(tmp_path):
    import os,sys
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env={**os.environ,'DANTZIG_DATA':str(tmp_path/'mcp')}
    params=StdioServerParameters(command=sys.executable,args=['-m','dantzig.mcp_server'],env=env)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            tools=await session.list_tools()
            assert {"dantzig_validate","dantzig_example","dantzig_save_problem","dantzig_solve","dantzig_records","dantzig_record"} <= {t.name for t in tools.tools}
            assert not (tmp_path/'mcp').exists()
            r=await session.call_tool('dantzig_solve',{'problem':example(),'seconds':5})
            assert not r.is_error
            # Text is the interoperable fallback, structuredContent may add a result envelope.
            data=json.loads(next(x.text for x in r.content if x.type=='text'))
            assert data['result']['status']=='optimal'
            assert data['result']['weighted_tardiness']==4
            loaded=await session.call_tool('dantzig_record',{'record_id':data['id']})
            assert not loaded.is_error
            exported=await session.call_tool('dantzig_export',{'document':data,'kind':'results'})
            assert not exported.is_error
            export_data=json.loads(next(x.text for x in exported.content if x.type=='text'))
            assert export_data['url'].endswith(export_data['id'])
            kept=await session.call_tool('dantzig_record',{'record_id':export_data['id']})
            assert json.loads(next(x.text for x in kept.content if x.type=='text'))['document']==data


def test_http_export_exact_and_durable(tmp_path,monkeypatch):
    monkeypatch.setenv('DANTZIG_DATA',str(tmp_path))
    with TestClient(app) as c:
        original={'name':'Borrador Ω 李明','jobs':[], 'integer':9007199254740993}
        export=c.post('/api/exports',json={'document':original}).json()
        downloaded=c.get(export['url'])
        assert downloaded.status_code==200 and downloaded.json()==original
        assert 'attachment' in downloaded.headers['content-disposition']
        assert export['filename'] in downloaded.headers['content-disposition']
        other=c.post('/api/problems',json=example()).json()
        assert c.get('/api/exports/'+other['id']).status_code==404
        assert c.get('/api/exports/missing').status_code==404
        assert c.post('/api/exports',json={'document':{},'kind':'other'}).status_code==422
    with TestClient(app) as c:
        assert c.get(export['url']).json()==original


@pytest.fixture
def anyio_backend():return 'asyncio'
