"""HTTP routes of the configurator (mounted by dantzig.app)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from . import service
from .catalog import CatalogError

router = APIRouter()
STATIC = Path(__file__).resolve().parent / "static"


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalog: dict[str, Any] | None = None
    catalog_id: str | None = None
    selections: dict[str, str | None] = Field(default_factory=dict)
    objective: list[dict[str, Any]] | None = None
    seconds: float = Field(default=10, gt=0, allow_inf_nan=False, description="Presupuesto total de la operación en segundos")
    save: bool = False


def _guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except CatalogError as e:
        raise HTTPException(422, str(e))
    except KeyError as e:
        raise HTTPException(404, f"No se encuentra {e.args[0]!r}")


@router.get("/configurator", include_in_schema=False)
def page():
    return FileResponse(STATIC / "configurator.html")


@router.get("/configurator/hoard-theme.css", include_in_schema=False)
def theme():
    return FileResponse(STATIC / "hoard-theme.css", media_type="text/css")


@router.get("/api/configurator/examples")
def examples():
    return service.example_list()


@router.get("/api/configurator/examples/{key}")
def example(key: str):
    return _guard(service.example, key)


@router.get("/api/configurator/catalogs")
def catalogs():
    return service.catalogs()


@router.post("/api/configurator/catalogs")
def save_catalog(catalog: dict[str, Any]):
    return _guard(service.save_catalog, catalog)


@router.get("/api/configurator/catalogs/{key}")
def get_catalog(key: str):
    return _guard(service.get_catalog, key)


@router.post("/api/configurator/{operation}")
def run(operation: Literal["propagate", "complete", "repair", "explain", "verify"], req: RunRequest):
    return _guard(service.run, operation, **req.model_dump())
