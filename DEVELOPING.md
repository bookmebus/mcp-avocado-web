# Developing polymcp — the framework & how to start

A hands-on guide to the framework this server is built on and the loop you use to
add to it. Read this after [README.md](./README.md) (what it is, how to run it)
and alongside [ROADMAP.md](./ROADMAP.md) (what to build next, and the verify gate
for each step).

Audience: a developer new to MCP who wants to add a tool or resource here and
prove it works.

---

## 1. What MCP is, in one minute

**MCP (Model Context Protocol)** is a standard way for an AI client (Claude Code,
the MCP Inspector, Claude Desktop) to talk to an external program — this *server*.
The client and server speak JSON-RPC over a *transport*. Here the transport is
**stdio**: the client launches `polymcp avocado` as a subprocess and exchanges
messages over stdin/stdout. No network, no port. That's why the registration
command in the README is just a shell command the client runs.

A server exposes three kinds of capability. The SDK gives you one decorator for
each:

| Primitive    | Decorator           | What it is                                              | Think of it as |
| ------------ | ------------------- | ------------------------------------------------------- | -------------- |
| **Tool**     | `@mcp.tool()`       | An action the model can call, with typed args + result  | a function     |
| **Resource** | `@mcp.resource(uri)`| Read-only data the model can fetch by URI               | a file / GET   |
| **Prompt**   | `@mcp.prompt()`     | A reusable prompt template the user can invoke          | a snippet      |

Today the shared core gives every server one tool (`health`) and no resources or
prompts yet. ROADMAP Step 2 adds a target tool; Step 3 adds the first resource.

---

## 2. The framework: MCP Python SDK **v2** (`MCPServer`)

- Package: **`mcp`** (installed: `mcp[cli]` **2.3.0**), the official Python SDK.
- The high-level server class is **`MCPServer`**, imported from
  `mcp.server.mcpserver` — see [src/mcp_core/server.py](./src/mcp_core/server.py).

> **Naming trap:** in SDK **v1** this same class was called **`FastMCP`** (from
> `mcp.server.fastmcp`). v2 renamed it to `MCPServer`. Most tutorials and blog
> posts online still say `FastMCP` — mentally substitute `MCPServer`.

You create one server object and decorate functions onto it. (In this repo that
creation is wrapped by `mcp_core.build_server` so every target shares it — §3/§5 —
but the underlying SDK usage is just this:)

```python
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("avocado-web", version="0.1.0")   # name + advertised version

@mcp.tool()
def ping() -> str:
    """Return 'pong' — a liveness check."""   # <-- becomes the tool description
    return "pong"

def main() -> None:
    mcp.run()        # transport="stdio" by default
```

Two things the SDK does for you automatically, and why the code looks the way it does:

- **Type hints become the schema.** `ping() -> str` tells the SDK the tool
  takes no arguments and returns a string. When you add args, annotate them — the
  SDK turns the signature into the JSON Schema the client validates against. Use
  Pydantic models for structured input/output (planned for Step 5).
- **The docstring becomes the description** the model reads to decide when to call
  the tool. Write it for the model: say *when to use it*, not how it's implemented.

### The `run()` transports

`mcp.run(transport=...)` accepts `"stdio"` (default, what we use), `"sse"`, or
`"streamable-http"`. We stay on stdio — it's the simplest and matches local
`claude mcp add`. The other two are for hosting the server over HTTP; out of scope
until/unless we deploy it.

---

## 3. How this project is wired

One repo, one MCP server **per target project**, over a shared core (full rationale
in §5):

```
src/
├── mcp_core/          # shared: factory, plugin contract, launcher, config helpers
│   ├── __init__.py    #   __version__ = distribution version
│   ├── server.py      #   build_server(ctx) → MCPServer + shared health tool
│   ├── plugin.py      #   TargetSpec — what each target plugin publishes
│   ├── registry.py    #   discover_targets() — walks mcp_targets/ for TARGET
│   ├── cli.py         #   `polymcp` launcher (run a target / --list)
│   └── config.py      #   REPO_ROOT (where the .env files live)
└── mcp_targets/
    ├── avocado/       # MCPServer "avocado-web" — __version__, TARGET, scoped config, tools
    └── cm_market_server/  # MCPServer "cm-market-server" (Spree + commission gem) — same shape
tests/                 # MIRRORS src/: tests/mcp_core/test_server.py ↔ src/mcp_core/server.py
pyproject.toml         # ONE launcher console script: polymcp
```

**The version chain (single source) + identity as config.** Version is build
identity; name/description are content. Both stay out of per-target code literals:

1. `mcp_core/__init__.py` holds the ONE `__version__` — the distribution version,
   read by hatch for the package.
2. `pyproject.toml` `[tool.hatch.version]` reads it, so the *packaged* version
   can't drift from code.
3. Each target `__init__.py` **re-exports** that `__version__` (no per-target
   literal) and puts it on `TARGET` as the `--list` default. The `server_name` /
   `description` **defaults** come from a committed plain-text `meta.toml` next to
   the code (via `load_meta(__file__)`) — never a brand literal in `.py`. At build
   time the target's **settings** supply the LIVE values, overridable from
   `.env.<target>` (`<PREFIX>_VERSION` / `_SERVER_NAME` / `_DESCRIPTION`,
   12-factor), which `build_server` applies to the handshake and the `health`
   tool. So version is single-sourced, and identity is **config, not literals**.

**The launcher (plugin model).** `pyproject.toml` `[project.scripts]` defines ONE
script: `polymcp = "mcp_core.cli:main"`. It discovers targets by walking
`mcp_targets/` for each package's `TARGET` (`mcp_core/registry.py`), then runs the
one you name: `uv run polymcp avocado` calls `TARGET.create()` (which calls that
target's `build(ctx)`) and `.run()`. Each invocation is still a separate
server process. Adding a target needs **no** change to pyproject or the core —
drop a folder that exposes a `TARGET`. (See §5 for the target contract.)

> **Two names, on purpose.** A target's **slug** (`TargetSpec.name`, e.g.
> `avocado`) is the CLI handle + `.env.<slug>`; its **server name**
> (`server_name`, e.g. `avocado-web`) is what an MCP client sees. They default to
> the same value — set `server_name` only when they must differ. Both are declared
> once, together, in the manifest.

**The arm64 pin.** `.python-version` forces a native Apple-Silicon interpreter so
`cryptography` installs as a prebuilt wheel. The README §"Why the Python version
is pinned to arm64" explains the full reason — you don't need to touch this.

---

## 4. The dev loop — how to actually start doing

Everything runs through **uv** (the package manager) and **pytest**. Four commands
cover the whole cycle:

```bash
uv sync                        # one-time / after changing deps: build the .venv
uv run pytest                  # the inner loop: run while you edit
uv run ruff check src tests    # lint (import order, unused, pyupgrade, bugbear)
uv run ruff format src tests   # format (owns whitespace — don't hand-align)
uv run polymcp --list          # which targets exist
uv run polymcp avocado         # start the avocado server on stdio (Ctrl-C) — manual smoke
npx @modelcontextprotocol/inspector uv run polymcp avocado   # click through tools in a UI
```

The **inner loop is `uv run pytest`**. Write or adjust a test, make it pass, repeat.
The golden rule from ROADMAP: *each step ships one capability and at least one test
that proves it; don't start the next step until this one is green.*

### Adding a new tool — the recipe

1. **Write the logic** in a module — `mcp_core/` if every target needs it, else
   the target's package (§5). Then register a thin tool in the target's
   `server.py`, decorated with `@mcp.tool()`. Annotate args + return; docstring for
   the model.
2. **Add a test at the mirrored path** — `tests/<same/dirs/as/src>/test_<module>.py`
   (e.g. `src/mcp_core/server.py` → `tests/mcp_core/test_server.py`),
   cheap-to-expensive, mirroring the existing ones:
   - the underlying logic returns what you expect (call the plain function),
   - edge/error cases produce a clear message,
   - the server actually *registers* the tool (the real MCP-wiring proof):
     ```python
     import asyncio
     from mcp_targets.avocado.server import build
     def test_tool_registered():
         mcp = build()   # fresh server; build() returns it ready
         names = {t.name for t in asyncio.run(mcp.list_tools())}
         assert "your_tool_name" in names
     ```
3. **Run `uv run pytest`** until green.
4. **Smoke it live** with the Inspector, then (optionally) in Claude Code.

A **resource** is the same recipe with `@mcp.resource("avocado://...")` and
`asyncio.run(mcp.list_resources())` in the test (ROADMAP Step 3).

### Worked example: the next step (ROADMAP Step 2)

Step 2 adds `avocado_web_version` — report *avocado-web's* latest git tag by
shelling out to the sibling repo. Sketch of what lands in `server.py`:

```python
import os, subprocess
from pathlib import Path

def _avocado_web_path() -> Path:
    # config: env var wins, else default to the sibling checkout
    return Path(os.environ.get("AVOCADO_WEB_PATH", Path(__file__).parents[3] / "avocado-web"))

@mcp.tool()
def avocado_web_version() -> str:
    """Return avocado-web's current release version (its latest git tag)."""
    path = _avocado_web_path()
    if not (path / ".git").is_dir():
        raise ValueError(f"avocado-web not found at {path}. Set AVOCADO_WEB_PATH.")
    return subprocess.run(
        ["git", "-C", str(path), "describe", "--tags", "--abbrev=0"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
```

Its test creates a throwaway git repo with a known tag in a `tmp_path`, points
`AVOCADO_WEB_PATH` at it, and asserts the tool returns that tag — no dependency on
your real checkout. That's the "shell out to the target repo" pattern the roadmap
calls the core reusable idea.

### uv tips — stay productive, avoid footguns

**uv** is the one tool that manages the Python version, the
virtualenv, and the dependencies. If you're coming from Ruby, the mental map is:
`uv` ≈ `bundler` + `rbenv`, `pyproject.toml` ≈ `Gemfile`, `uv.lock` ≈
`Gemfile.lock`, `uv run` ≈ `bundle exec`.

Daily-driver commands:

```bash
uv run <cmd>          # run a command INSIDE the project env (uv run pytest, uv run polymcp avocado)
uv sync               # make the .venv exactly match uv.lock (safe to run anytime; no-op if current)
uv add <pkg>          # add a dependency — edits pyproject.toml AND uv.lock, then installs
uv add --dev <pkg>    # add a DEV-only dependency (like pytest) to the [dependency-groups] dev list
uv remove <pkg>       # remove a dependency (keeps pyproject + lock in sync)
uv lock               # re-resolve the lockfile without installing
uv tree               # show the dependency tree (what pulled in what)
```

The habits that prevent the common mistakes:

- **Always `uv run`, never a bare `python`/`pytest`.** A bare `python` uses
  whatever interpreter is on your PATH — likely a system one that can't see `mcp`,
  giving a confusing `ModuleNotFoundError`. `uv run pytest` always uses this
  project's `.venv`. (You almost never need to "activate" the venv by hand.)
- **Add deps with `uv add`, don't hand-edit `pyproject.toml`.** `uv add` updates
  the lockfile in the same step, so the two can't drift. If you *do* edit
  `pyproject.toml` by hand, run `uv sync` right after to reconcile.
- **Commit `uv.lock`.** It pins exact versions so everyone (and CI) installs the
  same tree — the Python equivalent of committing `Gemfile.lock`. Never add it to
  `.gitignore`.
- **Don't commit `.venv/`.** It's machine-specific and already git-ignored; it's
  rebuildable anytime with `uv sync`. If the env ever feels broken, the reliable
  reset is `rm -rf .venv && uv sync`.
- **Respect the arm64 pin.** `.python-version` fixes the interpreter (see README
  for why). Don't "fix" an install error by pointing uv at a different Python
  without reading that section first — it's deliberate.
- **Lockfile out of date?** If `uv run` warns that the lock is stale, run
  `uv sync` (or `uv lock`) rather than ignoring it — a stale lock is how "works on
  my machine" bugs start.
- **One version bump, one place.** To release, edit `__version__` in
  `mcp_core/__init__.py` — the single source every target re-exports (§3). Then
  `uv sync` so build metadata refreshes;
  don't touch a version in `pyproject.toml` — there isn't one to touch.

---

## 5. Structure rules — keep it testable, DRY, boilerplate-free

Right now everything fits in `server.py`. It won't for long: the roadmap adds a
git helper (Step 2), a resource (Step 3), a config home (Step 4), and an HTTP
client (Step 5). These rules keep that growth clean. The **one idea** behind all
of them: *`server.py` is wiring, not logic.*

### How this maps to MVC / SOA (if you think in Rails)

Coming from BookMeBus Rails apps, reach for **SOA / service objects**, not MVC.
MVC is a *web UI* pattern and only partly fits here: an MCP server has **no View**
— the AI client is the consumer, and a tool's return value + docstring *is* the
"view contract." What carries over cleanly is the service-object discipline you
already use in `operator-tenant/app/models/service/*.rb` and `*/app/services/`: a
thin request surface delegating to focused service classes.

| Rails concept                     | MCP server equivalent                                    |
| --------------------------------- | -------------------------------------------------------- |
| Controller (kept thin)            | the `@mcp.tool()` / `@mcp.resource()` function           |
| Routes                            | registering those on the `mcp` object in `server.py`     |
| Service object (`app/services/`)  | the logic modules: `git.py`, `api/client.py`, …          |
| Model (data shape)                | a **Pydantic** model / dataclass                         |
| View                              | *none* — the client renders; your return value is the API|

So "fat model, skinny controller" becomes **skinny tool, logic in services** —
which is exactly Rules 1–5 below. The server is itself one *service* in the wider
BookMeBus SOA: it sits beside avocado-web and talks over a boundary, never reaching
into another app's internals.

### Rule 1 — Separate logic from MCP wiring (this is what makes it testable)

A tool function should be **thin**: it delegates to a plain Python function that
knows nothing about MCP. Test the plain function directly (fast, no async, no
server); keep the one small "is it registered?" test for the wiring.

```python
# git.py  — plain logic, trivially testable (give it a path, get a string back)
def latest_tag(repo_path: Path) -> str:
    ...

# server.py — thin wiring, no logic of its own
@mcp.tool()
def avocado_web_version() -> str:
    """Return avocado-web's current release version."""
    return latest_tag(_avocado_web_path())
```

Why: a function that takes its inputs as **arguments** and **returns** a value
(no hidden globals, no I/O baked in) can be tested by just calling it. A tool body
full of logic can only be tested through the whole MCP machinery — slow and
awkward. If a test is hard to write, the code is too tangled; fix the shape, not
the test. This is exactly why the tests are layered: cheap logic tests first, the
server-registration (wiring) test last.

### Rule 2 — Isolate side effects behind small functions

Anything that touches the outside world — `subprocess` (git), `os.environ`, HTTP,
the filesystem — goes in its own small, named function. Pure logic stays separate
from it. Tests then point that one function at a **temp git repo**, a fake env, or
a **recorded HTTP response** (roadmap Step 5) instead of hitting the real world.
Never call a network/subprocess directly inside a tool body.

### Rule 3 — One home for config (don't read env vars everywhere)

The moment a second piece of code needs the repo path or an API URL, put all
settings in one module (`config.py`, roadmap Step 4) and import from there. Don't
sprinkle `os.environ["..."]` across files — that's the classic non-DRY trap: the
default changes and you fix it in four places and miss one.

```python
# config.py — a typed SCHEMA + a source-agnostic STORE.
# The schema is just typed fields. env_store backs it with this target's env +
# .env.<slug>, scoped to a prefix DERIVED from the folder name (avocado → AVOCADO_).
class AvocadoSettings(BaseModel):
    web_path: Path = _DEFAULT_CHECKOUT   # ← AVOCADO_WEB_PATH
    web_dsn: str | None = None           # ← AVOCADO_WEB_DSN (Step 5)

def make_settings():                     # called from build(), NOT at import
    return env_store(AvocadoSettings, slug_from(__package__))   # read `settings.values.web_path`
```

(Same principle as the version: **one source of truth** — here the folder name —
derived, never copied. See §3.)

Each target's `SettingsStore` is **scoped by its prefix**: avocado reads only
`AVOCADO_*`, cm-market only `CM_MARKET_SERVER_*`, so one target can't read
another's vars even in the same process. Values come from the real environment and
the target's **own** gitignored `.env.<target>` (plus an optional shared `.env`),
with precedence **real env > `.env.<target>` > `.env` > default** — and the values
are **typed and validated**, so a bad DSN fails loudly instead of at first use.
The **source is swappable** (`mcp_core.settings`): `EnvSource` in prod,
`MemorySource` in tests, `JsonFileSource` or a `DbSource` for durable/dynamic
config — pass one as an `overlay=` to make the store **writable** (`settings.set(...)`).
Copy the matching `.env.<target>.example` to start. Secrets live in env /
`.env.<target>` only — never committed. (This fulfilled roadmap Step 4, early.)

### Rule 4 — Let the SDK generate the boilerplate; don't write it by hand

Don't hand-write JSON schemas, argument validation, or the tool description blob.
Type hints become the schema, the docstring becomes the description (§2). For
structured input/output use a **Pydantic model** once and let the SDK derive the
rest. The less plumbing you write, the less there is to get wrong.

### Rule 5 — Grow by concern; shared plumbing in the core, specifics in the target

Two axes now. Anything target-agnostic (git, HTTP, config helpers) goes in
`mcp_core` and is written once; anything specific to one project (its tools, its
defaults) goes in that `mcp_targets/<target>/`. Each target's `server.py` stays a
flat table of contents — "what this server exposes." Shape as features land:

```
src/
├── mcp_core/                         # shared — written & tested ONCE
│   ├── server.py   # build_server() factory + common tools
│   ├── plugin.py   # TargetSpec — the target plugin contract
│   ├── registry.py # discover_targets() — convention discovery
│   ├── cli.py      # `polymcp` launcher
│   ├── config.py   # REPO_ROOT (per-target Settings live in each target)
│   ├── git.py      # shell-out-to-repo helpers                     (Step 2)
│   └── http.py     # app-token (Doorkeeper) client base            (Step 5)
└── mcp_targets/
    └── avocado/                      # one per target, THIN
        ├── __init__.py # re-exports the dist __version__ + TARGET
        ├── config.py   # schema (identity + AVOCADO_WEB_PATH …) + make_settings()
        └── server.py   # build(ctx): build_server(ctx, settings.values) + tools
```

Decide per feature: *does every target need this?* → `mcp_core`. *Is it specific
to one project?* → that target. When a tool body grows past a few lines, that logic
belongs in a module (core or target), not in the decorator.

> **Why one repo, not a copy per project.** The plumbing (version/git/http/config)
> is identical across targets; putting it in `mcp_core` means a fix lands once and
> every server gets it — no drift, the same principle as the single-source version.
> Escalate to a **uv workspace** (separate pyproject per package, shared lock) only
> if two targets ever need different dependency versions or independent deploys.

### Rule 5b — Many tools, many teams: one module per department

A single target (avocado) will grow dozens of tools across departments —
reservations, finance, operations, support. Don't pile them into `server.py`.
Give each department a module under `tools/`, exposing one `register(mcp, settings)`
hook; `server.py` imports the modules and calls each. It stays a flat list of "which
departments are wired in," and a team owns its file without touching anyone else's.
(This is the MCP echo of Rails controller namespaces — `admin/`, `portal/`, …)

```
src/mcp_targets/avocado/
├── server.py          # build(ctx): reservations.register(mcp, settings); finance.register(…)
└── tools/
    ├── reservations.py   # def register(mcp, settings): @mcp.tool() find_reservation, trips_today
    └── finance.py        # def register(mcp, settings): @mcp.tool() payment_status
```

```python
# tools/reservations.py — the whole department contract is one function
from mcp.server.mcpserver import MCPServer
from mcp_core.settings import SettingsStore
from mcp_targets.avocado.config import AvocadoSettings

def register(mcp: MCPServer, settings: SettingsStore[AvocadoSettings]) -> None:
    @mcp.tool()
    def find_reservation(code: str) -> str:
        """Look up a reservation by booking code."""
        ...   # reads config via settings.values.<field>

# server.py — one line per department
from mcp_targets.avocado.tools import finance, reservations
def build(ctx):
    mcp = build_server(ctx)
    settings = make_settings()
    reservations.register(mcp, settings)
    finance.register(mcp, settings)
```

Each department is tested at its mirrored path
(`tests/mcp_targets/avocado/tools/test_reservations.py`) by calling `register` on a
throwaway `build_server(...)` and asserting its tool names — the department in
isolation, no real server started. One more test on the composed server asserts all
departments' tools are present. (As tools reach the real API, keep the body thin:
`register` wires the tool; the logic lives in a service module — Rules 1–2.)

### Rule 6 — Every new capability ships a test, in the same change

Non-negotiable, straight from the ROADMAP: one capability, at least one test that
proves it, and the previous step green before you start the next. A tool with no
test isn't done. Tests live under `tests/`, laid out to **mirror `src/`**:
`tests/mcp_core/test_server.py` ↔ `src/mcp_core/server.py`, so each test maps to its
module while staying out of the shipped package. Pytest is configured
(`pyproject.toml` `[tool.pytest.ini_options]`): `testpaths = ["tests"]`,
`pythonpath = ["src"]`, and `--import-mode=importlib` so the same-named
`test_server.py` files across the mirrored tree coexist.

### The smell test

Before committing, ask: *Could I test this without starting the server?* If no,
Rule 1/2 is being broken. *Did I copy a value or an env lookup that already lives
somewhere?* If yes, Rule 3 — import it instead. *Am I hand-writing something the
SDK could derive?* If yes, Rule 4 — delete it.

---

## 6. Quick reference

**`MCPServer` surface you'll use** (from the installed `mcp` 2.3.0):

- Decorators: `@mcp.tool(...)`, `@mcp.resource(uri, ...)`, `@mcp.prompt(...)`
- Imperative registration: `mcp.add_tool(...)`, `mcp.add_resource(...)`
- Introspection (handy in tests, all async): `mcp.list_tools()`,
  `mcp.list_resources()`, `mcp.list_prompts()`, `mcp.read_resource(uri)`
- Run: `mcp.run(transport="stdio")`
- `@mcp.tool(annotations=...)` takes a `ToolAnnotations` for hints like
  `readOnlyHint` / `openWorldHint` — ROADMAP Step 5 uses these to mark the first
  API tool as safe and outward-reaching.

**Conventions in this repo**

- Build in small steps; every capability has a test; keep the next step blocked
  until the current one is green (ROADMAP).
- One source of truth for the version (§3); never hardcode it twice.
- Write tool docstrings for the model (when to use), not for a human reviewer.
- Keep the shared core clean enough that **each new target is a thin add-on**
  (cm-market-server, …) — note what's generic vs. avocado-specific as you go
  (ROADMAP Step 7).
- Ruby 2.3 / Rails 4.2 live in avocado-web; this server is **Python only** and
  talks *about* avocado-web — it never imports or runs Ruby.

**Where to look when stuck**

- SDK API shape — `uv run python -c "from mcp.server.mcpserver import MCPServer; print([m for m in dir(MCPServer) if not m.startswith('_')])"`
- Official docs & Inspector — https://modelcontextprotocol.io and
  `npx @modelcontextprotocol/inspector`
- What to build next and its verify gate — [ROADMAP.md](./ROADMAP.md)
