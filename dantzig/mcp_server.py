"""Static discovery; neither import nor tools/list opens the database."""
from mcp.server.mcpserver import MCPServer
from . import service

mcp = MCPServer("Dantzig's Hoard")


@mcp.tool()
def dantzig_example() -> dict:
    """Get an invented six-job problem and all explicit model fields."""
    return service.example()


@mcp.tool()
def dantzig_save_problem(problem: dict) -> dict:
    """Validate and save an immutable scheduling problem. Times are integral."""
    return service.save_problem(problem)


@mcp.tool()
def dantzig_solve(problem: dict, seconds: float = 10) -> dict:
    """Schedule alternative resources, release dates, deadlines, precedence and family changes. Returns optimal/feasible/infeasible/unknown and persists the exact input with its result."""
    return service.solve_problem(problem, seconds)


@mcp.tool()
def dantzig_records() -> list[dict]:
    """List persisted problems and runs."""
    return service.catalog()


@mcp.tool()
def dantzig_record(record_id: str) -> dict:
    """Read/export a saved problem or run, including original assumptions."""
    return service.load(record_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
