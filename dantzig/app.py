from fastapi import FastAPI, HTTPException

from fastapi.responses import FileResponse, Response
import json
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from . import service
from .models import Problem, SolveRequest, ExportRequest
from .solver import VerificationError
from .configurator.api import router as configurator_router
from .hoard_link.copilot import install_copilot

app = FastAPI(title="Dantzig's Hoard")

static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")

app.include_router(configurator_router)
install_copilot(app, "dantzig", os.environ.get("DANTZIG_DATA", str(Path(__file__).resolve().parents[1] / "data")), app_name="Dantzig's Hoard")


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


@app.post("/api/exports")
def export(request: ExportRequest):
    return service.export_document(request.document, request.kind)


@app.get("/api/exports/{key}")
def download(key: str):
    try:
        record = service.load(key)
    except KeyError:
        raise HTTPException(404, "No se encuentra esa exportación")
    if record["kind"] != "export":
        raise HTTPException(404, "Ese documento no es una exportación")
    return Response(json.dumps(record["document"], ensure_ascii=False, indent=2),
                    media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{record["name"]}"'})


@app.post("/api/solve")
def solve(request: SolveRequest):
    try:
        return service.solve_problem(request.problem.model_dump(), request.seconds)
    except ValueError as error:
        raise HTTPException(422, str(error))
    except VerificationError as error:
        raise HTTPException(500, str(error))
