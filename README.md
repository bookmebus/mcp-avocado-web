# avocado-mcp

An MCP (Model Context Protocol) server for **avocado-web** — the BookMeBus core
(Rails 4.2 system of record). Built in small, individually verifiable steps so
the design is easy to trace and later **replicate to the commissioner monorepo**.

- **Runtime:** Python 3.13 / MCP Python SDK **v2** (`mcp[cli]`, class `MCPServer` — was `FastMCP` in v1)
- **Package manager:** [uv](https://docs.astral.sh/uv/)
- **Tests:** pytest
- **Transport:** stdio (local)

> This is a standalone tool. It talks *about* avocado-web; it is not part of the
> Rails app and does not depend on Ruby.

## Layout

```
mcp-avocado-web/
├── pyproject.toml            # uv + hatchling; version read from the package (no drift)
├── src/avocado_mcp/
│   ├── __init__.py           # __version__ — single source of truth
│   └── server.py             # FastMCP server + get_version tool
└── tests/
    └── test_version.py       # smoke tests (constant → function → registered tool)
```

## Quick start

```bash
cd mcp-avocado-web
uv sync                       # create .venv and install deps (incl. dev group)
uv run pytest                 # run the smoke tests  → 3 passed
uv run avocado-mcp            # start the server (stdio); Ctrl-C to stop
```

Inspect it interactively with the MCP Inspector (SDK-agnostic):

```bash
npx @modelcontextprotocol/inspector uv run avocado-mcp
```

### Why the Python version is pinned to arm64

`.python-version` pins `cpython-3.13.5-macos-aarch64`. This is deliberate: on
Apple Silicon, `mcp` pulls in `cryptography`, which no longer ships Intel-macOS
(x86_64) wheels. A Homebrew Intel Python (`/usr/local/...`) forces a from-source
Rust build that fails (needs `rustc ≥ 1.83`). Running on a native **arm64**
interpreter installs `cryptography` as a prebuilt wheel — no compiler needed.
`uv sync` honours the pin automatically. (When replicating to an Intel host or
CI, pick an arm64 or Linux interpreter, or a Python with matching wheels.)

## Register with Claude Code

From the workspace, add it as a local stdio server (example):

```bash
claude mcp add avocado-web -- uv --directory /Users/channaly/Project/bookmebus/mcp-avocado-web run avocado-mcp
```

Then call the `get_version` tool — it returns this server's version (currently
`0.1.0`) and doubles as a reachability health check.

## Status

**Step 1 — scaffold + `get_version`.** Done. See [ROADMAP.md](./ROADMAP.md) for
what each subsequent step adds and how it is verified.
