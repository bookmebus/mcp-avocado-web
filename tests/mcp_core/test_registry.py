"""The registry discovers target plugins by convention, in isolation.

Mirrors src/mcp_core/registry.py.
"""

import mcp_core.registry as registry
from mcp_core.plugin import TargetSpec
from mcp_core.registry import discover_targets


def test_discovers_shipped_targets_with_no_errors() -> None:
    disc = discover_targets()
    assert {"avocado", "cm-market-server", "demo"} <= set(disc.targets)
    assert disc.errors == {}  # the repo's targets all import cleanly


def test_a_broken_target_is_isolated_not_fatal(monkeypatch) -> None:
    # Make importing the demo package blow up; discovery must record it and keep
    # the healthy targets working — not raise.
    real_import = registry.importlib.import_module

    def fake_import(name, *args, **kwargs):
        if name.endswith(".demo"):
            raise ImportError("boom")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(registry.importlib, "import_module", fake_import)
    disc = discover_targets()
    assert "demo" in disc.errors and "ImportError" in disc.errors["demo"]  # recorded
    assert "avocado" in disc.targets  # others still found


def test_each_discovered_target_is_a_valid_spec() -> None:
    for name, spec in discover_targets().targets.items():
        assert isinstance(spec, TargetSpec)
        assert spec.name == name  # keyed by its own declared slug
        assert spec.version  # carries its version
        assert spec.description  # non-empty one-liner
        assert callable(spec.build)  # can be built


def test_create_uses_the_specs_declared_identity() -> None:
    spec = discover_targets().targets["avocado"]
    assert spec.name == "avocado"  # CLI slug
    assert spec.mcp_name == "avocado-web"  # distinct client-facing server name
    mcp = spec.create()  # create() wires identity in — no repetition
    assert mcp.name == "avocado-web"
    assert mcp.version == spec.version
