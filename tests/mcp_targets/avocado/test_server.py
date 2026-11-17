"""Tests for the avocado target server. Mirrors src/mcp_targets/avocado/server.py."""

import asyncio
import json

from mcp_targets.avocado import TARGET, __version__

mcp = TARGET.create()  # build with the target's own declared identity


def test_avocado_identity() -> None:
    assert mcp.name == "avocado-web"
    assert mcp.version == __version__


def test_avocado_has_shared_health_tool() -> None:
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "health" in names  # inherited from mcp_core (reports identity)


def test_avocado_composes_department_tools() -> None:
    # The server wires every department's tools together via register(mcp, settings).
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"find_reservation", "trips_today"} <= names  # reservations dept
    assert "payment_status" in names  # finance dept


def test_identity_is_config_not_code(monkeypatch) -> None:
    # name / version / description are CONTENT: env vars rebrand/re-version the
    # RUNNING server (handshake + `health`) without any code change (12-factor).
    monkeypatch.setenv("AVOCADO_DESCRIPTION", "Rebranded via env")
    monkeypatch.setenv("AVOCADO_SERVER_NAME", "my-bus")
    monkeypatch.setenv("AVOCADO_VERSION", "9.9.9")
    srv = TARGET.create()  # a fresh build reads the overrides
    payload = json.loads(asyncio.run(srv.call_tool("health", {})).content[0].text)
    assert payload == {
        "server": "my-bus",
        "version": "9.9.9",
        "description": "Rebranded via env",
        "status": "ok",
    }
    assert srv.name == "my-bus" and srv.version == "9.9.9"  # handshake reflects it too
    # `--list`'s static catalog keeps the defaults (discovery does no import-time I/O).
    assert TARGET.description != "Rebranded via env"
    assert TARGET.mcp_name != "my-bus"
