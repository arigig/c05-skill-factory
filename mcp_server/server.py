"""Local MCP server exposing the one governed tool for this project:
publish_to_catalog. Run directly (`python -m mcp_server.server`) to serve
over stdio for an MCP client (e.g. Claude Code) to connect to.

This module is intentionally thin — all the real logic, validation, and
audit logging live in app/catalog.py, which is unit-tested independently of
the MCP transport layer.
"""
from mcp.server.mcpserver import MCPServer

from app.catalog import PublishError, publish_to_catalog

mcp = MCPServer(
    name="c05-skill-factory-catalog",
    title="C05 Skill Factory — Catalog Tool",
    description="Governed tool for publishing approved conversion runs into the reusable asset catalog.",
    version="1.0.0",
)


@mcp.tool(
    name="publish_to_catalog",
    description=(
        "Publish an approved conversion run's generated Python code into the reusable catalog. "
        "Refuses any run whose reviewer status is not 'approved', and refuses to republish a run "
        "already in the catalog. Never accepts a filesystem path — only a run_id."
    ),
)
def publish_to_catalog_tool(run_id: str) -> dict:
    """Publish an approved run to the catalog.

    Args:
        run_id: The conversion run's UUID, as shown by the reviewer UI/API.
    """
    try:
        return publish_to_catalog(run_id, caller="mcp-client")
    except PublishError as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
