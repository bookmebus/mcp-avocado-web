"""Step 1 smoke tests.

Three layers, cheapest first:
1. the version constant is well-formed,
2. the tool function returns that constant,
3. the FastMCP server actually *exposes* a tool named `get_version`.

Layer 3 is the real proof that MCP wiring works, not just a plain function.
"""

import asyncio

from avocado_mcp import __version__
from avocado_mcp.server import get_version, mcp


def test_version_is_semver() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3, f"expected MAJOR.MINOR.PATCH, got {__version__!r}"
    assert all(p.isdigit() for p in parts), f"non-numeric segment in {__version__!r}"


def test_get_version_returns_package_version() -> None:
    assert get_version() == __version__


def test_server_exposes_get_version_tool() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert "get_version" in names, f"get_version not registered; found {names}"
