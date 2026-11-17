"""cm-market-server MCP server — composition root.

Same shape as the avocado target, different target. The package `__init__` wraps
`build` in a `TargetSpec`; the launcher runs it:

    uv run polymcp cm-market-server    # starts this server on stdio

No departments yet; `build()` constructs settings only to give the shared server
its live (env-overridable) identity. Add `register(mcp, settings)` calls when the
first department lands.
"""

from mcp.server.mcpserver import MCPServer

from mcp_core.plugin import BuildContext
from mcp_core.server import build_server
from mcp_targets.cm_market_server.config import make_settings


def build(ctx: BuildContext) -> MCPServer:
    """Create the cm-market-server server (identity from this target's settings)."""
    settings = make_settings()
    return build_server(ctx, settings.values)
