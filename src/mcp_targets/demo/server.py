"""demo MCP server — composition root.

The minimal shape every target follows: build the shared server (identity from
env-loaded settings), register each department, return it. Run it:

    uv run polymcp demo        # starts this server on stdio
"""

from mcp.server.mcpserver import MCPServer

from mcp_core.plugin import BuildContext
from mcp_core.server import build_server
from mcp_targets.demo.config import make_settings
from mcp_targets.demo.tools import basics


def build(ctx: BuildContext) -> MCPServer:
    """Create the demo server with its shared + department tools."""
    settings = make_settings()  # constructed here, not at import
    mcp = build_server(ctx, settings.values)  # live, env-overridable identity

    basics.register(mcp, settings)

    return mcp
