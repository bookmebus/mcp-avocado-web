"""basics department registers its tools. Mirrors .../demo/tools/basics.py."""

import asyncio

from mcp.server.mcpserver import MCPServer

from mcp_targets.demo.config import make_settings
from mcp_targets.demo.tools import basics


def test_register_attaches_basics_tools() -> None:
    mcp = MCPServer("test", version="0.0.0")  # register in isolation, no full build
    basics.register(mcp, make_settings())
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"echo", "greet", "set_greeting"} <= names
