"""The avocado-web MCP server.

Step 1 (current): expose a single `get_version` tool that returns this
server's own version. This proves the full plumbing end to end — package,
server, tool registration, and tests — before any avocado-web integration.

Built on the MCP Python SDK v2 (`MCPServer`, formerly `FastMCP` in v1).

Run it:
    uv run avocado-mcp          # stdio transport, for an MCP client
"""

from mcp.server.mcpserver import MCPServer

from avocado_mcp import __version__

# `version=` lets the SDK advertise our version in the server handshake, and we
# pass the same __version__ the tool returns — one source of truth, two surfaces.
mcp = MCPServer("avocado-web", version=__version__)


@mcp.tool()
def get_version() -> str:
    """Return the version of this avocado-web MCP server.

    Use this as a health check to confirm the server is reachable and to
    see which build of the server a client is talking to.
    """
    return __version__


def main() -> None:
    """Console-script entry point (see pyproject `[project.scripts]`)."""
    mcp.run()  # defaults to the stdio transport


if __name__ == "__main__":
    main()
