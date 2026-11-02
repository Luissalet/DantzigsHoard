"""MCP tools of the configurator; ``register(mcp)`` is called by dantzig.mcp_server."""
from __future__ import annotations

from typing import Any

from . import service


def dantzig_config_examples() -> list[dict]:
    """List bundled example catalogs (synthetic) usable as catalog_id."""
    return service.example_list()


def dantzig_config_example(catalog_id: str) -> dict:
    """Get a bundled example catalog: slots, options with attrs/price/stock, and rules (requires, excludes, compare, sum)."""
    return service.example(catalog_id)


def dantzig_config_save_catalog(catalog: dict) -> dict:
    """Validate and save a product catalog for configuration; returns its id. Saved catalogs are immutable."""
    return service.save_catalog(catalog)


def dantzig_config_catalogs() -> list[dict]:
    """List saved configuration catalogs."""
    return service.catalogs()


def dantzig_config_propagate(selections: dict | None = None, catalog_id: str | None = None, catalog: dict | None = None, seconds: float = 10) -> dict:
    """For every slot, which options remain possible given the other selections, which are forced, and whether all selections fit together."""
    return service.run("propagate", catalog=catalog, catalog_id=catalog_id, selections=selections, seconds=seconds)


def dantzig_config_complete(selections: dict | None = None, catalog_id: str | None = None, catalog: dict | None = None, objective: list[dict] | None = None, seconds: float = 10, save: bool = False) -> dict:
    """Fill the unset slots keeping the selections; objective is a lexicographic list like [{"attr":"price","sense":"min"}] (attr may be price, count or any numeric option attribute). Returns status optimal/feasible/infeasible/inconclusive, configuration and BOM."""
    return service.run("complete", catalog=catalog, catalog_id=catalog_id, selections=selections, objective=objective, seconds=seconds, save=save)


def dantzig_config_repair(selections: dict | None = None, catalog_id: str | None = None, catalog: dict | None = None, objective: list[dict] | None = None, seconds: float = 10, save: bool = False) -> dict:
    """Change the fewest selections to reach a valid configuration (several at once when needed), then optimise objective. Lists the changes and the original conflicts."""
    return service.run("repair", catalog=catalog, catalog_id=catalog_id, selections=selections, objective=objective, seconds=seconds, save=save)


def dantzig_config_explain(selections: dict, catalog_id: str | None = None, catalog: dict | None = None, seconds: float = 10) -> dict:
    """Why selections cannot go together: every minimal conflicting subset of selections with the minimal rules (or stock shortage) behind it."""
    return service.run("explain", catalog=catalog, catalog_id=catalog_id, selections=selections, seconds=seconds)


def dantzig_config_verify(selections: dict | None = None, catalog_id: str | None = None, catalog: dict | None = None, objective: list[dict] | None = None, seconds: float = 10) -> dict:
    """Cross-check complete and repair against brute-force enumeration (small catalogs only)."""
    return service.run("verify", catalog=catalog, catalog_id=catalog_id, selections=selections, objective=objective, seconds=seconds)


TOOLS = [
    dantzig_config_examples,
    dantzig_config_example,
    dantzig_config_save_catalog,
    dantzig_config_catalogs,
    dantzig_config_propagate,
    dantzig_config_complete,
    dantzig_config_repair,
    dantzig_config_explain,
    dantzig_config_verify,
]


def register(mcp: Any) -> None:
    for fn in TOOLS:
        mcp.tool()(fn)
