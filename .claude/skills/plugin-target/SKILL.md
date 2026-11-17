---
name: plugin-target
description: Use when adding a NEW target (a whole MCP server for another project/app/service) to this repo, or changing how targets are discovered/launched/configured. Targets are plugins — drop a folder under src/mcp_targets/ that exposes a TARGET; the launcher finds it. Config is a typed pydantic schema bound by env_store to a source-agnostic SettingsStore (env/memory/json; db-ready), scoped by a folder-derived prefix.
---

# Adding a target (plugin model)

A **target** is a self-contained MCP server for one project or service
(this repo ships `avocado`, `cm-market-server`). Targets are **plugins**: the core never
names them. You add one by dropping a folder — no edit to `pyproject.toml`,
`mcp_core`, or any other target.

## The contract: expose a `TARGET`

Each target package's `__init__.py` publishes one value the launcher discovers:

```python
# src/mcp_targets/<name>/__init__.py  — the manifest: `--list` defaults
from mcp_core import __version__          # re-export the ONE distribution version
from mcp_core.config import slug_from
from mcp_core.plugin import TargetSpec
from mcp_targets.<name>.config import DEFAULT_DESCRIPTION
from mcp_targets.<name>.server import build

TARGET = TargetSpec(
    name=slug_from(__package__),          # CLI slug + the .env.<name> it loads (structural)
    version=__version__,                  # dist version; <PREFIX>_VERSION overrides at runtime
    description=DEFAULT_DESCRIPTION,       # from config; <PREFIX>_DESCRIPTION overrides
    build=build,
    # server_name=DEFAULT_SERVER_NAME,    # ONLY if the client name differs from the slug
)
```

Keep **identity as content, not literals** (12-factor): `version`, `server_name`,
and `description` are fields on the Settings schema, so they load from
`.env.<name>` and override at runtime. `version` is single-sourced — the manifest
re-exports `mcp_core.__version__`, never a per-target literal. The manifest values
are the `--list` defaults (discovery does no import-time I/O); `build()` passes the
LIVE settings into `build_server(ctx, settings.values)`, which applies them to the
handshake and the `health` tool.

Discovery (`mcp_core/registry.py`) walks `mcp_targets/` and collects every
subpackage whose `TARGET` is a `TargetSpec`, returning a `Discovery(targets,
errors)`: a target that fails to import lands in `errors` (keyed by slug) instead
of raising, so one broken target can't crash `--list` or the others. The launcher
(`mcp_core/cli.py`, the `polymcp` script) runs the one you name via `spec.create()`:

```
uv run polymcp --list        # all targets
uv run polymcp <name>         # run one on stdio
```

## `server.py` — a `build(ctx)` that returns a ready server

Identity is NOT hardcoded here — `build_server(ctx, settings.values)` applies the
target's LIVE settings (name / version / description, all env-overridable) to the
handshake and the shared `health` tool. So a target needs **no** identity tool of
its own, and no identity literals in code.

```python
from mcp_core.plugin import BuildContext

def build(ctx: BuildContext) -> MCPServer:
    settings = make_settings()                          # constructed HERE, not at import
    mcp = build_server(ctx, settings.values)            # live, env-overridable identity + `health`
    reservations.register(mcp, settings)                # each department (see `departments`)
    return mcp                                           # add tools; keep local paths OUT of output
```

`build()` returns a fresh server (no module-level singleton) and **constructs the
settings itself** — so merely *discovering* a target reads no env files, tests
build throwaway instances (`TARGET.create()`), and a target that fails to import
is isolated (see the discovery note above), never crashing the launcher.

## `config.py` — a typed schema + a source-agnostic store

Config is split: a **schema** (a plain pydantic `BaseModel` — just typed fields)
and a **source** (where values live, behind `mcp_core.settings`). `env_store`
binds them, backing the schema with this target's env + `.env.<slug>`, scoped to a
prefix **derived from the folder name** — the scope boundary (a target can't read
another's vars). A `make_settings()` factory returns the `SettingsStore`; `build()`
calls it (never at import). Read typed values via `settings.values.<field>`, write
via `settings.set(...)`.

```python
from pydantic import BaseModel

from mcp_core import __version__ as _DIST_VERSION
from mcp_core.config import load_meta, slug_from
from mcp_core.settings import SettingsStore, env_store   # + MemorySource / JsonFileSource for writes

# Content (description, server_name) lives in a committed `meta.toml` NEXT TO this
# file — plain text, never a brand/string literal in .py.
_META = load_meta(__file__)
DEFAULT_DESCRIPTION = _META["description"]
DEFAULT_SERVER_NAME = _META.get("server_name", slug_from(__package__))

class MyAppSettings(BaseModel):                  # the typed SCHEMA, nothing else
    version: str = _DIST_VERSION                 # ← <PREFIX>_VERSION (default: build version)
    server_name: str = DEFAULT_SERVER_NAME       # ← <PREFIX>_SERVER_NAME (client-facing name)
    description: str = DEFAULT_DESCRIPTION        # ← <PREFIX>_DESCRIPTION (shown by `health`)
    repo_path: Path = _DEFAULT_CHECKOUT          # ← <PREFIX>_REPO_PATH
    dsn: str | None = None                       # ← <PREFIX>_DSN   (Step 5; see `db-access`)

def make_settings() -> SettingsStore[MyAppSettings]:   # called from build(), NOT at import
    return env_store(MyAppSettings, slug_from(__package__))             # read-only (env-backed)
    # writable: env_store(MyAppSettings, slug_from(__package__), overlay=MemorySource())
```

- **Derivation:** folder `my_app` → slug `my-app` → prefix `MY_APP_` + files
  `.env` and `.env.my-app`. You hand-write only the typed **fields**.
- Field `x_y` maps to source key `<PREFIX>_X_Y` (e.g. `dsn` → `MY_APP_DSN`).
- **Read:** `settings.values.repo_path` (typed/validated, autocompletes).
  **Write:** `settings.set("dsn", …)` — validated, then persisted to the first
  *writable* source. Env-only stores are
  read-only and `set` raises `ReadOnlySettings`.
- **Swap the source** without touching the schema: `EnvSource` (prod),
  `MemorySource` (tests/runtime overrides), `JsonFileSource` (durable) — or a
  `DbSource` you add with the same `get`/`set`. Pass one as `overlay=` to layer it
  over env (overlay wins on read, receives writes).
- **Precedence:** no overlay → real env > `.env.<slug>` > `.env` > default. With
  an overlay it sits on top (so a runtime `set` takes effect): overlay > real env
  > `.env.<slug>` > `.env` > default.
- Env files live at **repo root**, never in `src/` (kept out of the wheel).

## Checklist for a new target

1. `src/mcp_targets/<name>/` with `__init__.py` (re-export `__version__` + `TARGET`),
   `server.py` (`build()`), `config.py` (`Settings` incl. identity fields),
   `meta.toml` (plain-text `description` / optional `server_name`), `tools/`
   (see `departments`).
2. `.env.<name>.example` at repo root (placeholders only); real `.env.<name>` is
   gitignored. Keep secrets there only (see `security`).
3. Tests mirroring `src/` under `tests/mcp_targets/<name>/`.
4. Nothing else. `polymcp --list` should now show it. Register it with a
   client as `... run polymcp <name>`.

## When to reach for entry points instead

Convention discovery assumes all targets live in **this repo**. If a target ever
ships as its **own installed package** or a third party provides one, switch
`registry.py` to `importlib.metadata` entry-point discovery — the `TargetSpec`
contract and the launcher stay the same.
