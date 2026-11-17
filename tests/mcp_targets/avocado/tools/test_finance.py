"""Finance department registers its tools. Mirrors .../tools/finance.py."""

import asyncio

from mcp.server.mcpserver import MCPServer

from mcp_targets.avocado.config import make_settings
from mcp_targets.avocado.tools import finance


def test_register_attaches_finance_tools() -> None:
    mcp = MCPServer("test", version="0.0.0")
    finance.register(mcp, make_settings())
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "payment_status" in names
