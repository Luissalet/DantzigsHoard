"""Configurator: CP-SAT results cross-checked against brute-force enumeration."""
from __future__ import annotations

import random

import pytest

from dantzig.configurator import CatalogError, check, complete, explain, load_catalog, propagate, repair, violations
from dantzig.configurator.examples import drive_kit
from dantzig.configurator.verify import enumerate_valid, space_size, verify_result


@pytest.fixture(scope="module")
def kit():
    return load_catalog(drive_kit())


def test_rule_semantics_by_hand(kit):
    ok = {"motor": "m15", "drive": "d2", "grid": "g400", "psu": "p25", "enclosure": "e_m", "brake": None, "cooling": None}
    assert violations(kit, ok) == []
    assert "volt_motor" in violations(kit, dict(ok, motor="m075"))
    assert "frame_fit" in violations(kit, dict(ok, motor="m55", drive="d75", enclosure="e_s"))
    assert "brake_needed" in violations(kit, dict(ok, motor="m55", drive="d75", enclosure="e_m"))
    assert "__stock__:motor:m30" in violations(kit, dict(ok, motor="m30", drive="d4"))
    # 24 V budget: d75 1.5 + b132 1.0 + hex 0.9 = 3.4 A > 2.5 A
    big = {"motor": "m55", "drive": "d75", "grid": "g400", "psu": "p25", "enclosure": "e_l", "brake": "b132", "cooling": "hex"}
    assert violations(kit, big) == ["aux_budget"]
    assert violations(kit, dict(big, psu="p5")) == []


def test_two_changes_needed(kit):
    sel = {"motor": "m075", "drive": "d2", "grid": "g690"}
    res = repair(kit, sel)
    assert res["status"] == "optimal"
    assert res["change_count"] == 2
    assert violations(kit, res["configuration"]) == []
    # no single change can fix it
    for slot in sel:
        rest = {k: v for k, v in sel.items() if k != slot}
        others_fixed = [a for a in enumerate_valid(kit, rest)]
        assert others_fixed == [], slot
    assert verify_result(kit, res, "repair")["agrees"]
    assert len(res["original_conflicts"]) >= 3


def test_explain_minimal_and_complete(kit):
    sel = {"motor": "m075", "drive": "d2", "grid": "g690", "enclosure": "e_s", "cooling": "hex"}
    ex = explain(kit, sel)
    assert ex["status"] == "infeasible" and ex["minimal"] and ex["exhaustive"]
    for c in ex["conflicts"]:
        chosen = {s["slot"]: s["option"] for s in c["selections"]}
        assert list(enumerate_valid(kit, chosen)) == []
        for drop in chosen:
            sub = {k: v for k, v in chosen.items() if k != drop}
            assert next(enumerate_valid(kit, sub), None) is not None
    # brute-force: every minimal infeasible pair/triple of selections is listed
    from itertools import combinations
    listed = {frozenset((s["slot"], s["option"]) for s in c["selections"]) for c in ex["conflicts"]}
    items = list(sel.items())
    for n in range(1, len(items) + 1):
        for comb in combinations(items, n):
            d = dict(comb)
            if next(enumerate_valid(kit, d), None) is None and all(
                next(enumerate_valid(kit, {k: v for k, v in comb if k != x}), None) is not None for x in d
            ):
                assert frozenset(comb) in listed


def test_stock_explained(kit):
    ex = explain(kit, {"motor": "m30"})
    assert ex["conflict"]["rules"][0]["kind"] == "stock"


def test_complete_matches_enumeration(kit):
    for sel in ({}, {"motor": "m55"}, {"cooling": "hex"}, {"motor": "m75h", "brake": "b132"}):
        res = complete(kit, sel)
        rep = verify_result(kit, res, "complete")
        assert rep["agrees"], (sel, rep)
    lex = [{"attr": "count", "sense": "min"}, {"attr": "price", "sense": "min"}]
    res = complete(kit, {"motor": "m15"}, objective=lex)
    assert verify_result(kit, res, "complete", lex)["agrees"]


def test_complete_infeasible(kit):
    res = complete(kit, {"motor": "m55", "enclosure": "e_s"})
    assert res["status"] == "infeasible"
    assert res["conflict"]["rules"][0]["id"] == "frame_fit"


def test_propagate_matches_enumeration(kit):
    sel = {"motor": "m55", "psu": "p25"}
    pr = propagate(kit, sel)
    for row in pr["slots"]:
        others = {k: v for k, v in sel.items() if k != row["slot"]}
        ref = {a[row["slot"]] for a in enumerate_valid(kit, others)}
        assert set(row["viable"]) == ref, row["slot"]
    assert pr["consistent"] is False  # m55 needs d75+b132+hex = 3.4 A > 2.5 A
    assert "p25" not in next(r for r in pr["slots"] if r["slot"] == "psu")["viable"]
    ok = propagate(kit, {"motor": "m55"})
    assert ok["consistent"] is True
    assert next(r for r in ok["slots"] if r["slot"] == "cooling")["forced"] == "hex"


def _random_catalog(rng: random.Random) -> dict:
    slots = []
    for i in range(rng.randint(3, 5)):
        opts = [
            {"id": f"o{j}", "price": rng.randint(1, 50), "stock": rng.choice([None, 0, 3]),
             "attrs": {"a": rng.randint(0, 9), "fam": rng.choice(["x", "y", "z"]), "w": rng.choice([0.5, 1, 1.5, 2])}}
            for j in range(rng.randint(2, 4))
        ]
        slots.append({"id": f"s{i}", "required": rng.random() < 0.7, "options": opts})
    rules = []
    ids = [s["id"] for s in slots]
    for k in range(rng.randint(2, 6)):
        t = rng.choice(["requires", "excludes", "compare", "sum"])
        a, b = rng.sample(ids, 2)
        sa = next(s for s in slots if s["id"] == a)
        sb = next(s for s in slots if s["id"] == b)
        if t == "requires":
            rules.append({"id": f"r{k}", "type": t, "if": {"slot": a, "option": rng.choice(sa["options"])["id"]},
                          "then": {"slot": b, "attr": "a", "op": rng.choice([">", "<=", "=="]), "value": rng.randint(0, 9)}})
        elif t == "excludes":
            rules.append({"id": f"r{k}", "type": t, "a": {"slot": a, "option": rng.choice(sa["options"])["id"]},
                          "b": {"slot": b, "options": [o["id"] for o in rng.sample(sb["options"], 1)]}})
        elif t == "compare":
            if rng.random() < 0.5:
                rules.append({"id": f"r{k}", "type": t, "left": {"slot": a, "attr": "fam"}, "op": "==", "right": {"slot": b, "attr": "fam"}})
            else:
                rules.append({"id": f"r{k}", "type": t, "left": {"slot": a, "attr": "a"}, "op": rng.choice(["<", ">=", "!="]),
                              "right": {"slot": b, "attr": "a"}, "factor": rng.choice([1, 0.5, 2]), "offset": rng.choice([0, 1, -1])})
        else:
            rules.append({"id": f"r{k}", "type": t, "slots": rng.sample(ids, 2), "attr": "w", "op": rng.choice(["<=", ">="]),
                          "value": rng.choice([1, 2, 2.5, 3])})
    return {"id": "rnd", "slots": slots, "rules": rules}


@pytest.mark.parametrize("seed", range(40))
def test_random_catalogs_against_enumeration(seed):
    rng = random.Random(seed)
    cat = load_catalog(_random_catalog(rng))
    valid = list(enumerate_valid(cat))
    res = check(cat, {})
    assert (res["status"] == "feasible") == bool(valid)
    if res["status"] == "feasible":
        assert violations(cat, res["example"]) == []
    sel = {}
    for s in cat.slots:
        if rng.random() < 0.6:
            sel[s.id] = rng.choice(s.values())
    c = complete(cat, sel)
    assert verify_result(cat, c, "complete")["agrees"], (seed, c)
    r = repair(cat, sel)
    assert verify_result(cat, r, "repair")["agrees"], (seed, r)
    ex = explain(cat, sel)
    feasible_sel = next(enumerate_valid(cat, sel), None) is not None
    assert (ex["status"] == "feasible") == feasible_sel


@pytest.mark.parametrize(
    "bad,msg",
    [
        ({"slots": []}, "no slots"),
        ({"slots": [{"id": "a", "options": [{"id": "x"}, {"id": "x"}]}]}, "duplicate option"),
        ({"slots": [{"id": "a", "options": [{"id": "x"}]}], "rules": [{"type": "requires", "if": {"slot": "a", "option": "y"}, "then": {"slot": "a", "chosen": True}}]}, "no option"),
        ({"slots": [{"id": "a", "options": [{"id": "x"}]}], "rules": [{"type": "magic"}]}, "unknown type"),
        ({"slots": [{"id": "a", "options": [{"id": "x"}]}], "rules": [{"type": "excludes", "a": {"slot": "a", "chosen": False}, "b": {"slot": "a", "option": "x"}}]}, "required"),
    ],
)
def test_catalog_validation(bad, msg):
    with pytest.raises(CatalogError, match=msg):
        load_catalog(bad)


def test_space_size(kit):
    assert space_size(kit) == 5 * 5 * 3 * 3 * 3 * 3 * 3


# --- HTTP and MCP -----------------------------------------------------------

def test_http_configurator(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from dantzig.app import app

    monkeypatch.setenv("DANTZIG_DATA", str(tmp_path))
    with TestClient(app) as c:
        assert c.get("/configurator").status_code == 200
        ex = c.get("/api/configurator/examples").json()
        assert ex[0]["id"] == "drive-kit"
        cat = c.get("/api/configurator/examples/drive-kit").json()
        saved = c.post("/api/configurator/catalogs", json=cat).json()
        assert c.get("/api/configurator/catalogs").json()[0]["id"] == saved["id"]
        sel = {"motor": "m075", "drive": "d2", "grid": "g690"}
        r = c.post("/api/configurator/repair", json={"catalog_id": saved["id"], "selections": sel, "save": True}).json()
        assert r["change_count"] == 2 and r["record_id"]
        assert c.get("/api/records/" + r["record_id"]).json()["kind"] == "config_run"
        p = c.post("/api/configurator/propagate", json={"catalog_id": "drive-kit", "selections": {"motor": "m55"}}).json()
        assert p["consistent"] is True
        v = c.post("/api/configurator/verify", json={"catalog_id": "drive-kit", "selections": sel}).json()
        assert v["agrees"]
        e = c.post("/api/configurator/explain", json={"catalog": cat, "selections": {"motor": "m30"}}).json()
        assert e["conflict"]["rules"][0]["kind"] == "stock"
        assert c.post("/api/configurator/complete", json={"catalog_id": "drive-kit", "selections": {"motor": "nope"}}).status_code == 422
        assert c.post("/api/configurator/complete", json={"catalog_id": "missing"}).status_code == 404
        assert c.post("/api/configurator/catalogs", json={"slots": []}).status_code == 422
        assert c.post("/api/configurator/teleport", json={}).status_code == 422


@pytest.mark.anyio
async def test_configurator_mcp_stdio(tmp_path):
    import json
    import os
    import sys

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = {**os.environ, "DANTZIG_DATA": str(tmp_path / "mcp")}
    params = StdioServerParameters(command=sys.executable, args=["-m", "dantzig.mcp_server"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert {"dantzig_config_propagate", "dantzig_config_complete", "dantzig_config_repair", "dantzig_config_explain", "dantzig_config_verify"} <= names
            r = await session.call_tool("dantzig_config_repair", {"catalog_id": "drive-kit", "selections": {"motor": "m075", "drive": "d2", "grid": "g690"}})
            assert not r.is_error
            data = json.loads(next(x.text for x in r.content if x.type == "text"))
            assert data["change_count"] == 2
            bad = await session.call_tool("dantzig_config_explain", {"catalog_id": "drive-kit", "selections": {"motor": "zzz"}})
            assert bad.is_error


@pytest.fixture
def anyio_backend():
    return "asyncio"
