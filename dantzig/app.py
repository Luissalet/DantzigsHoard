from fastapi import FastAPI, HTTPException

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from . import service
from .models import Problem, SolveRequest
from .solver import VerificationError
from .configurator.api import router as configurator_router

app = FastAPI(title="Dantzig's Hoard")

static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")

app.include_router(configurator_router)


@app.get("/")
def home():
    return FileResponse(static / "index.html")


@app.get("/api/health")
def health():
    return {"service": "dantzig-hoard", "version": "0.1.0"}


@app.get("/api/example")
def example():
    return service.example()


@app.get("/api/records")
def records():
    return service.catalog()


@app.get("/api/records/{key}")
def record(key: str):
    try:
        return service.load(key)
    except KeyError:
        raise HTTPException(404, "No se encuentra ese documento")


@app.post("/api/problems")
def save(problem: Problem):
    return service.save_problem(problem.model_dump())


@app.post("/api/validate")
def validate(problem: Problem):
    return problem.model_dump()


@app.post("/api/solve")
def solve(request: SolveRequest):
    try:
        return service.solve_problem(request.problem.model_dump(), request.seconds)
    except ValueError as error:
        raise HTTPException(422, str(error))
    except VerificationError as error:
        raise HTTPException(500, str(error))
