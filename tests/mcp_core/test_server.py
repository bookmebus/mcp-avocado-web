"""Tests for the shared factory. Mirrors src/mcp_core/server.py."""

import asyncio
import json

from mcp_core.plugin import BuildContext
from mcp_core.server import build_server

CTX = BuildContext(name="svc", version="9.9.9", description="a test server")


def test_build_server_sets_name_and_version() -> None:
    mcp = build_server(CTX)
    assert mcp.name == "svc"
    assert mcp.version == "9.9.9"


def test_build_server_registers_shared_health() -> None:
    names = {t.name for t in asyncio.run(build_server(CTX).list_tools())}
    assert "health" in names, f"shared tool missing; found {names}"


def test_health_reports_identity_and_status() -> None:
    result = asyncio.run(build_server(CTX).call_tool("health", {}))  # exercises the tool path
    payload = json.loads(result.content[0].text)
    assert payload == {
        "server": "svc",
        "version": "9.9.9",
        "description": "a test server",
        "status": "ok",
    }
