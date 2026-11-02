"""Configurator service shared by HTTP and MCP: catalogs persisted next to scheduling records."""
from __future__ import annotations

from typing import Any

from .. import service as store
from . import examples
from .catalog import CatalogError, load_catalog
from .solver import complete, explain, propagate, repair
from .verify import MAX_ENUMERATION, space_size, verify_result

OPERATIONS = ("propagate", "complete", "repair", "explain", "verify")


def example_list() -> list[dict[str, Any]]:
    return [{"id": k, "name": f()["name"]} for k, f in examples.CATALOGS.items()]


def example(key: str) -> dict[str, Any]:
    if key not in examples.CATALOGS:
        raise KeyError(key)
    return examples.CATALOGS[key]()


def save_catalog(data: dict[str, Any]) -> dict[str, Any]:
    cat = load_catalog(data)
    return store.save("catalog", {"name": cat.name, "catalog": cat.to_dict()})


def catalogs() -> list[dict[str, Any]]:
    return [r for r in store.catalog() if r["kind"] == "catalog"]


def get_catalog(key: str) -> dict[str, Any]:
    rec = store.load(key)
    if rec.get("kind") != "catalog":
        raise KeyError(key)
    return rec


def _resolve(catalog: dict[str, Any] | None, catalog_id: str | None) -> tuple[dict[str, Any], str | None]:
    if catalog is not None:
        return catalog, None
    if catalog_id:
        if catalog_id in examples.CATALOGS:
            return examples.CATALOGS[catalog_id](), catalog_id
        return get_catalog(catalog_id)["catalog"], catalog_id
    raise CatalogError("hace falta 'catalog' o 'catalog_id'")


def run(
    operation: str,
    *,
    catalog: dict[str, Any] | None = None,
    catalog_id: str | None = None,
    selections: dict[str, Any] | None = None,
    objective: list[dict[str, Any]] | None = None,
    seconds: float = 10,
    save: bool = False,
) -> dict[str, Any]:
    if operation not in OPERATIONS:
        raise CatalogError(f"operación desconocida {operation!r}; usa una de {', '.join(OPERATIONS)}")
    if not seconds > 0:
        raise CatalogError("seconds debe ser positivo: es el presupuesto total de la operación")
    raw, cid = _resolve(catalog, catalog_id)
    cat = load_catalog(raw)
    sel = selections or {}
    if operation == "propagate":
        result = propagate(cat, sel, time_limit=seconds)
    elif operation == "complete":
        result = complete(cat, sel, objective=objective, time_limit=seconds)
    elif operation == "repair":
        result = repair(cat, sel, objective=objective, time_limit=seconds)
    elif operation == "explain":
        result = explain(cat, sel, time_limit=seconds)
    else:
        size = space_size(cat)
        if size > MAX_ENUMERATION:
            raise CatalogError(f"el catálogo tiene {size} combinaciones; la comprobación por enumeración admite hasta {MAX_ENUMERATION}")
        c = complete(cat, sel, objective=objective, time_limit=seconds)
        r = repair(cat, sel, objective=objective, time_limit=seconds)
        result = {
            "space": size,
            "complete": verify_result(cat, c, "complete", objective),
            "repair": verify_result(cat, r, "repair", objective),
        }
        result["agrees"] = result["complete"]["agrees"] and result["repair"]["agrees"]
    result["operation"] = operation
    result["catalog"] = {"id": cid, "name": cat.name}
    if save:
        rec = store.save("config_run", {"name": f"{cat.name} · {operation}", "catalog_id": cid, "catalog": cat.to_dict(),
                                        "selections": sel, "objective": objective, "result": result})
        result["record_id"] = rec["id"]
    return result
