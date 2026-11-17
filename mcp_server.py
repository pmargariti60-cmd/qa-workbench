"""Read-only local MCP integration for Codex."""

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from workbench import WORKBENCH_URL, list_runs, read_run

server = FastMCP("QA Workbench")


@server.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_qa_runs(limit: int = 10) -> list[dict[str, Any]]:
    """List recent completed QA runs with environment, result, and run ID."""
    return list_runs(max(1, min(limit, 30)))


@server.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_qa_run(run_id: str) -> dict[str, Any]:
    """Get the checks, observed failures, profile, and evidence links for a completed run."""
    run = read_run(run_id)
    for check in run["checks"]:
        if screenshot := check.get("screenshot"):
            check["screenshot_url"] = f"{WORKBENCH_URL}/evidence/{run_id}/{screenshot}"
    return run


if __name__ == "__main__":
    server.run(transport="stdio")
