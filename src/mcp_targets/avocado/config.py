"""avocado-web settings — a typed schema backed by a read-only env source.

`AvocadoSettings` is the typed shape; `env_store` backs it with this target's env
+ `.env.avocado`, scoped to `AVOCADO_*` (derived from the folder name). It is
read-only — deploy-time config, not runtime-writable. `settings` is a
`SettingsStore`: read a field as `settings.values.web_path`. Field `x_y` maps to
env var `AVOCADO_X_Y`. Secrets live in env / `.env.avocado` only — never committed.

Display metadata (version / server_name / description) are CONTENT, not logic:
they live here as defaults and load from `.env.avocado` (12-factor). The `version`
default is the distribution's single source, not a per-target literal.
"""

from pathlib import Path

from pydantic import BaseModel

from mcp_core import __version__ as _DIST_VERSION
from mcp_core.config import load_meta, slug_from
from mcp_core.settings import SettingsStore, env_store

# Default checkout: a sibling `avocado-web` next to this repo, derived from this
# file's location — no absolute path baked in. parents[4] walks
# config.py -> avocado -> mcp_targets -> src -> <repo> -> <workspace>.
# Override with AVOCADO_WEB_PATH.
_DEFAULT_CHECKOUT = Path(__file__).resolve().parents[4] / "avocado-web"

# Display defaults come from `meta.toml` (plain text) — no brand literal in code.
_META = load_meta(__file__)
DEFAULT_SERVER_NAME = _META.get("server_name", slug_from(__package__))
DEFAULT_DESCRIPTION = _META["description"]


class AvocadoSettings(BaseModel):
    version: str = _DIST_VERSION  # AVOCADO_VERSION — default is the build version
    server_name: str = DEFAULT_SERVER_NAME  # AVOCADO_SERVER_NAME — client-facing name
    description: str = DEFAULT_DESCRIPTION  # AVOCADO_DESCRIPTION — shown by `health`
    web_path: Path = _DEFAULT_CHECKOUT  # AVOCADO_WEB_PATH   — local avocado-web checkout
    web_dsn: str | None = None  # AVOCADO_WEB_DSN    — read-only MySQL (Step 5)
    api_base_url: str | None = None  # AVOCADO_API_BASE_URL (Step 5)
    client_id: str | None = None  # AVOCADO_CLIENT_ID  (Step 5)
    client_secret: str | None = None  # AVOCADO_CLIENT_SECRET (Step 5)


def make_settings() -> SettingsStore[AvocadoSettings]:
    """Build this target's settings store. Called from `build()` — NOT at import,
    so merely discovering the target reads no env files. Read-only (env-backed)."""
    return env_store(AvocadoSettings, slug_from(__package__))
