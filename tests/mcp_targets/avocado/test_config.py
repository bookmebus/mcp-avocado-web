"""avocado settings are typed and scoped to AVOCADO_*. Mirrors .../avocado/config.py.

Proves the two guarantees of the scoped-config design, via the settings store:
  1. a real env var (AVOCADO_*) is read, overriding the default;
  2. another target's var (CM_MARKET_SERVER_*) is invisible — no cross-target leak.
We build a fresh store inside each test so the monkeypatched env is applied.
"""

import mcp_targets.avocado.config as config
from mcp_targets.avocado.config import AvocadoSettings, make_settings


def test_description_default_comes_from_meta_toml() -> None:
    # The brand/description is CONTENT in plain text (meta.toml), not a .py literal.
    import tomllib
    from pathlib import Path

    meta_path = Path(config.__file__).parent / "meta.toml"
    meta = tomllib.loads(meta_path.read_text())
    assert config.DEFAULT_DESCRIPTION == meta["description"]


def test_no_settings_built_at_import_time() -> None:
    # P2: the store is constructed in build() via make_settings(), NOT at import,
    # so merely importing (or discovering) a target reads no env files.
    assert not hasattr(config, "settings")
    assert callable(config.make_settings)


def test_reads_its_own_env_var(monkeypatch) -> None:
    monkeypatch.setenv("AVOCADO_WEB_DSN", "mysql+pymysql://mcp_ro:x@localhost/avocado")
    assert make_settings().values.web_dsn == "mysql+pymysql://mcp_ro:x@localhost/avocado"


def test_default_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("AVOCADO_WEB_DSN", raising=False)
    s = make_settings().values
    assert s.web_dsn is None  # typed optional default
    assert s.web_path.name == "avocado-web"  # derived sibling default


def test_does_not_read_another_targets_vars(monkeypatch) -> None:
    # A cm-market var must not leak into avocado (its prefix is AVOCADO_, not CM_MARKET_SERVER_).
    monkeypatch.setenv("CM_MARKET_SERVER_DSN", "postgresql+psycopg://leak@localhost/x")
    assert "dsn" not in AvocadoSettings.model_fields  # avocado schema has no bare `dsn`
    assert "path" not in AvocadoSettings.model_fields  # nor cm-market's `path`
    assert make_settings().values.web_dsn is None  # avocado's own field unaffected
