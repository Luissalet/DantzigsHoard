"""Shared native application service used by both HTTP and MCP."""
from pathlib import Path
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from .models import Problem, SolveRequest
from .solver import solve


@contextmanager
def connect():
    root = Path(os.environ.get("DANTZIG_DATA", Path(__file__).resolve().parents[1] / "data"))
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "dantzig.db", timeout=30)
    try:
        with db:
            db.execute("CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)")
            yield db
    finally:
        db.close()


def save(kind, body):
    key = str(uuid.uuid4())
    with connect() as db:
        db.execute("INSERT INTO records(id,kind,body) VALUES(?,?,?)", (key, kind, json.dumps(body, ensure_ascii=False)))
    return {"id": key, **body}


def load(key):
    with connect() as db:
        row = db.execute("SELECT kind,body FROM records WHERE id=?", (key,)).fetchone()
    if not row:
        raise KeyError(key)
    return {"id": key, "kind": row[0], **json.loads(row[1])}


def catalog():
    with connect() as db:
        return [{"id": key, "kind": kind, "name": json.loads(body).get("name", "Plan"), "created": created}
                for key, kind, body, created in db.execute("SELECT id,kind,body,created FROM records ORDER BY rowid DESC")]


def save_problem(problem: dict):
    return save("problem", Problem.model_validate(problem).model_dump())


def solve_problem(problem: dict, seconds: float = 10):
    request = SolveRequest(problem=problem, seconds=seconds)
    result = solve(request.problem, request.seconds)
    return save("run", {"name": request.problem.name, "problem": request.problem.model_dump(), "result": result})


def example():
    raw = [("A",6,8,12,"a"),("B",4,7,7,"b"),("C",9,5,11,"a"),("D",5,4,9,"b"),("E",3,6,18,"a"),("F",7,3,14,"b")]
    return Problem(name="Taller · seis pedidos de ejemplo", resources=["Máquina 1", "Máquina 2"], family_change=3,
                   jobs=[dict(id=k,durations={"Máquina 1":a,"Máquina 2":b},due=d,family=f) for k,a,b,d,f in raw]).model_dump()
