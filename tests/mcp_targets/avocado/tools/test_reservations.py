"""Reservations department registers its tools. Mirrors .../tools/reservations.py."""

import asyncio

from mcp.server.mcpserver import MCPServer

from mcp_targets.avocado.config import make_settings
from mcp_targets.avocado.tools import reservations


def test_register_attaches_reservation_tools() -> None:
    # register() onto a throwaway server — tests the department in isolation,
    # without starting the real avocado server.
    mcp = MCPServer("test", version="0.0.0")
    reservations.register(mcp, make_settings())
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"find_reservation", "trips_today"} <= names
