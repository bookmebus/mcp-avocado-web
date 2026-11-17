"""cm-market-server settings — a typed schema backed by a read-only env source.

Same shape as the avocado target, scoped to `CM_MARKET_SERVER_*` (from the slug
`cm-market-server`). `settings` is a `SettingsStore`: read a field as
`settings.values.path`. Field `x` maps to env var `CM_MARKET_SERVER_X`. Secrets
live in env / `.env.cm-market-server` only.

Display metadata (version / server_name / description) load from the env too.
"""

from pathlib import Path

from pydantic import BaseModel

from mcp_core import __version__ as _DIST_VERSION
from mcp_core.config import load_meta, slug_from
from mcp_core.settings import SettingsStore, env_store

# Default: a sibling `cm-market-server` next to this repo. The real checkout is
# usually elsewhere, so set CM_MARKET_SERVER_PATH. parents[4] walks
# config.py -> cm_market_server -> mcp_targets -> src -> <repo> -> <workspace>.
_DEFAULT_CHECKOUT = Path(__file__).resolve().parents[4] / "cm-market-server"

_SLUG = slug_from(__package__)
# Display defaults come from `meta.toml` (plain text) — no brand literal in code.
_META = load_meta(__file__)
DEFAULT_SERVER_NAME = _META.get("server_name", _SLUG)
DEFAULT_DESCRIPTION = _META["description"]


class CmMarketSettings(BaseModel):
    version: str = _DIST_VERSION  # CM_MARKET_SERVER_VERSION — default is the build version
    server_name: str = DEFAULT_SERVER_NAME  # CM_MARKET_SERVER_SERVER_NAME — client-facing name
    description: str = DEFAULT_DESCRIPTION  # CM_MARKET_SERVER_DESCRIPTION — shown by `health`
    path: Path = _DEFAULT_CHECKOUT  # CM_MARKET_SERVER_PATH — local checkout
    dsn: str | None = None  # CM_MARKET_SERVER_DSN  — read-only Postgres (Step 5)


def make_settings() -> SettingsStore[CmMarketSettings]:
    """Build this target's settings store. Called from `build()`, not at import."""
    return env_store(CmMarketSettings, _SLUG)
