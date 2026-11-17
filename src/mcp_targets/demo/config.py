"""demo settings — a typed schema + a swappable, writable source.

`DemoSettings` is just the typed shape. `env_store` backs it with this target's
env + `.env.demo`, and the `MemorySource` overlay makes it **writable** at runtime
(reads prefer the overlay, then env, then the default). `settings` is a
`SettingsStore`: read a field as `settings.values.greeting`, write via `settings.set(...)`.

Display metadata (version / server_name / description) load from the env too.
"""

from pydantic import BaseModel

from mcp_core import __version__ as _DIST_VERSION
from mcp_core.config import load_meta, slug_from
from mcp_core.settings import MemorySource, SettingsStore, env_store

_SLUG = slug_from(__package__)
# Display defaults come from `meta.toml` (plain text) — no brand literal in code.
_META = load_meta(__file__)
DEFAULT_SERVER_NAME = _META.get("server_name", _SLUG)
DEFAULT_DESCRIPTION = _META["description"]


class DemoSettings(BaseModel):
    version: str = _DIST_VERSION  # DEMO_VERSION — default is the build version
    server_name: str = DEFAULT_SERVER_NAME  # DEMO_SERVER_NAME — client-facing name
    description: str = DEFAULT_DESCRIPTION  # DEMO_DESCRIPTION — shown by `health`
    greeting: str = "Hello"  # DEMO_GREETING — prefix used by greet()


def make_settings() -> SettingsStore[DemoSettings]:
    """Build this target's settings store. Called from `build()`, not at import.

    A `MemorySource` overlay makes it writable, so `set_greeting` can change the
    greeting at runtime (reads prefer the overlay, then env, then the default)."""
    return env_store(DemoSettings, _SLUG, overlay=MemorySource())
