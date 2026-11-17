# polymcp

A small framework for running **many MCP (Model Context Protocol) servers from
one shared core**. Each server is a **target**: a self-contained plugin
discovered by convention and run through one launcher, `polymcp <target>`, with
its own typed, scoped config. Add a target by dropping a folder — the core names
no target.

- **Runtime:** Python 3.14 / MCP Python SDK **v2** (`mcp[cli]`, class `MCPServer` — was `FastMCP` in v1)
- **Config:** typed schema (pydantic) + a source-agnostic store — each target is scoped to its own prefix and reads/writes via a swappable source (env, in-memory, or JSON today; add your own, e.g. a database); copy `.env.<target>.example`
- **Package manager:** [uv](https://docs.astral.sh/uv/)
- **Tests:** pytest
- **Transport:** stdio (local)

> **Targets in this repo.** A generic **`demo`** target (BookMeBus-free, zero
> config — copy it to start your own), plus two BookMeBus targets as a real-world
> example: **avocado** (`avocado-web`, the Rails 4.2 core) and
> **cm-market-server** (the BookMe+ Spree marketplace). All are plugins *on* the
> framework, not part of it; see [PUBLISHING.md](./PUBLISHING.md) for stripping the
> BookMeBus ones to open-source the framework alone.

## Layout

A shared core holds the plumbing + the launcher; each target is a self-contained
package discovered by convention — add a target by dropping a folder. (See
[DEVELOPING.md](./DEVELOPING.md) §5 for the design and why.)

```
mcp-avocado-web/                      # checkout dir (dist name is `polymcp`; folder rename pending)
├── pyproject.toml                    # one launcher console script: polymcp
├── src/
│   ├── mcp_core/                     # SHARED, target-agnostic — written once
│   │   ├── __init__.py               #   __version__ (distribution version)
│   │   ├── server.py                 #   build_server(ctx) factory + shared health tool
│   │   ├── plugin.py                 #   TargetSpec — the plugin contract
│   │   ├── registry.py               #   discover_targets() — walks mcp_targets/
│   │   ├── cli.py                     #   `polymcp` launcher (run / --list)
│   │   ├── config.py                 #   slug/prefix/env-file derivations
│   │   └── settings.py               #   SettingsStore + sources (env/memory/json; db-ready)
│   └── mcp_targets/
│       ├── demo/                     # generic example target (framework demo, no BookMeBus)
│       │   ├── __init__.py           #   re-exports __version__ + TARGET
│       │   ├── meta.toml             #   description (plain-text content, not code)
│       │   ├── config.py             #   Settings scoped to DEMO_*
│       │   ├── server.py             #   build() → shared server + basics department
│       │   └── tools/basics.py       #   echo, greet, set_greeting
│       ├── avocado/                  # BookMeBus core (Rails 4.2)
│       │   ├── __init__.py           #   __version__ + TARGET (plugin descriptor)
│       │   ├── config.py             #   AvocadoSettings schema + env_store, scoped to AVOCADO_*
│       │   ├── server.py             #   build() → shared server + each department
│       │   └── tools/                #   one module per department, each register(mcp, settings)
│       │       ├── reservations.py   #     find_reservation, trips_today
│       │       └── finance.py        #     payment_status
│       └── cm_market_server/         # BookMe+ (Spree + commission gem) — scoped to CM_MARKET_SERVER_*
└── tests/                            # MIRRORS src/ — e.g. tests/mcp_core/test_server.py
```

## Quick start

```bash
cd mcp-avocado-web
uv sync                            # create .venv and install deps (incl. dev group)
uv run pytest                      # run the smoke tests
uv run polymcp --list              # show the available targets
uv run polymcp demo                # start the zero-config demo server (stdio); Ctrl-C to stop
```

Inspect it interactively with the MCP Inspector (SDK-agnostic):

```bash
npx @modelcontextprotocol/inspector uv run polymcp avocado
```

### Why the interpreter choice matters (arm64)

`.python-version` pins `3.14` (latest 3.14 patch). On Apple Silicon this must
resolve to a native **arm64** interpreter, and `uv` picks one automatically here.
Reason: `mcp` pulls in `cryptography`, which no longer ships Intel-macOS (x86_64)
wheels. A Homebrew Intel Python (`/usr/local/...`) forces a from-source Rust build
that fails (needs `rustc ≥ 1.83`). A native arm64 interpreter installs
`cryptography` as a prebuilt wheel — no compiler needed. (When replicating to an
Intel host or CI, pick an arm64 or Linux interpreter, or a Python with matching
wheels.)

## Register with Claude Code

Each target is a **separate** stdio server — same launcher, different target name:

```bash
REPO="$(pwd)"   # run this from the repo root; uv needs an absolute path
claude mcp add avocado-web      -- uv --directory "$REPO" run polymcp avocado
claude mcp add cm-market-server -- uv --directory "$REPO" run polymcp cm-market-server
```

Then call each server's shared `health` tool — it returns `{server, version,
description, status}`: a reachability check that exercises the tool path (distinct
from the MCP handshake) and the single place each target's identity is reported.

## Status

**Step 1 — scaffold + shared `health` tool.** Done. See [ROADMAP.md](./ROADMAP.md)
for what each subsequent step adds and how it is verified.
