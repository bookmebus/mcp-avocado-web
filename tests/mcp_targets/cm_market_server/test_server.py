"""Tests for the cm-market-server target. Mirrors src/mcp_targets/cm_market_server/server.py."""

import asyncio

from mcp_targets.cm_market_server import TARGET, __version__

mcp = TARGET.create()  # build with the target's own declared identity


def test_cm_market_server_identity() -> None:
    assert mcp.name == "cm-market-server"
    assert mcp.version == __version__


def test_cm_market_server_exposes_shared_health() -> None:
    # No departments yet — it exposes the shared health tool (which reports identity).
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "health" in names
