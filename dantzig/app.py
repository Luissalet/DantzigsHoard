from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from . import service
from .models import Problem, SolveRequest

app = FastAPI(title="Dantzig's Hoard")


@app.get("/")
def home():
    return RedirectResponse("/docs")


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


@app.post("/api/solve")
def solve(request: SolveRequest):
    try:
        return service.solve_problem(request.problem.model_dump(), request.seconds)
    except ValueError as error:
        raise HTTPException(422, str(error))
