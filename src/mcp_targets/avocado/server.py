"""avocado-web MCP server — composition root.

A thin plugin: build the shared server (identity from this target's env-loaded
settings), and wire each department's tools. The package `__init__` wraps `build`
in a `TargetSpec`; the launcher runs it:

    uv run polymcp avocado        # starts this server on stdio
"""

from mcp.server.mcpserver import MCPServer

from mcp_core.plugin import BuildContext
from mcp_core.server import build_server
from mcp_targets.avocado.config import make_settings
from mcp_targets.avocado.tools import finance, reservations


def build(ctx: BuildContext) -> MCPServer:
    """Create the avocado server (identity from the launcher's context) with its tools."""
    # Settings are constructed HERE (not at import), so discovery stays cheap.
    settings = make_settings()

    # Shared core gives us the server + `health`, with the LIVE (env-overridable)
    # name / version / description from settings — no identity literals in code.
    mcp = build_server(ctx, settings.values)

    # Each department registers its own tools, given the server + the settings.
    # Add a department by writing tools/<name>.py with register(mcp, settings).
    reservations.register(mcp, settings)
    finance.register(mcp, settings)

    return mcp
