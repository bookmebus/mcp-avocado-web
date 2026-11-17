"""Tests for the demo target. Mirrors src/mcp_targets/demo/server.py."""

import asyncio

from mcp_targets.demo import TARGET, __version__

mcp = TARGET.create()  # build with the target's own declared identity


def test_demo_identity() -> None:
    assert mcp.name == "demo"
    assert mcp.version == __version__


def test_demo_has_shared_and_department_tools() -> None:
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "health" in names  # shared, from mcp_core
    assert {"echo", "greet", "set_greeting"} <= names  # basics department
