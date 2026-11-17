# polymcp roadmap

Small, traceable steps. **Each step ships one capability and at least one test
that proves it.** Don't start a step until the previous step's tests are green.
The end goal is a shared core clean enough that **each new target is a thin add-on**
(avocado-web, cm-market-server, …) — so every step notes what carries over vs. what
is avocado-specific.

Legend: `[x]` done · `[ ]` todo · each step lists its **Verify** gate.

---

## Step 1 — Scaffold + self-version `[x]`

Prove the plumbing before touching avocado-web.

- [x] uv project; `MCPServer` (MCP Python SDK v2) exposing `health`
- [x] pytest smoke tests: constant well-formed → function → tool registered
- [x] arm64 Python pin (native `cryptography` wheel; see README for the why)
- [x] **refactored into the shared-core layout** (`mcp_core` + `mcp_targets/*`,
      see Step 7): `health` now comes from `mcp_core.build_server`.
- **Verify:** `uv run pytest` green; `uv run polymcp avocado` starts on stdio.
- **Replicable:** everything here is the shared skeleton every target reuses.

## Step 2 — Read avocado-web's real version `[ ]`

First real integration: report the target repo's version, not our own.

- [ ] Config: resolve the avocado-web repo path (env var `AVOCADO_WEB_PATH`,
      default `../avocado-web` relative to this repo).
- [ ] `avocado_web_version` tool: return the latest git tag of that repo
      (today: `2.22.0`), via `git -C <path> describe --tags --abbrev=0`.
- [ ] Actionable errors: path missing / not a git repo / no tags → a message
      that says exactly what to fix.
- **Verify:** unit test with a temp git repo + tag; manual call returns `2.22.0`.
- **Replicable:** the config + "shell out to the target repo" pattern is the core
  reusable idea. cm-market-server would point its own `CM_MARKET_SERVER_PATH` at
  its repo.

## Step 3 — Project facts resource `[ ]`

Move from "a tool" to "the server knows the project."

- [ ] An MCP **resource** (e.g. `avocado://project/info`) exposing stack facts
      from CLAUDE.md / Gemfile.lock: Rails 4.2.8, Ruby 2.3.8, default branch
      `develop`, remote `bookmebus/avocado`.
- [ ] Decide verified-vs-derived provenance for each fact (read live vs. pinned).
- **Verify:** resource lists; values match the repo; test asserts the schema.

## Step 4 — Config & packaging hardening `[~]`

- [x] Centralize settings: a typed per-target schema bound by `env_store` to a
      source-agnostic `SettingsStore` (`mcp_core/settings.py`), scoped by a
      folder-derived prefix. Reads are typed/validated; the source is swappable
      (env / memory / JSON today; db-ready) and writable via an overlay. (Done early.)
- [x] `ruff` lint + format configured (`[tool.ruff]`, rules E/W/F/I/UP/B, line 100);
      `uv run ruff check` and `uv run ruff format --check` both clean.
- [ ] `.mcp.json` example and `claude mcp add` snippet verified end to end.
- **Verify:** `uv run ruff check` clean; server registers in Claude Code.

## Step 5 — First read-only API tool `[ ]`

Reach the running app, not just the repo on disk. Scope to ONE safe endpoint.

- [ ] Pick one read-only `/api/v2` endpoint; add an HTTP client with the
      app-token (`client_id`/`client_secret`) flow against **staging**.
- [ ] Tool with Pydantic input/output schemas; secrets from env, never logged.
- [ ] `readOnlyHint: true`, `openWorldHint: true` annotations.
- **Verify:** recorded-response test (no live creds in CI); manual call on staging.

## Step 6 — Evaluations `[ ]`

- [ ] 10 read-only eval questions per the mcp-builder evaluation guide.
- **Verify:** eval harness passes against the server.

## Step 7 — Second target: cm-market-server `[~]`

**Design changed (2026-11-13): shared core, not copy-paste.** Instead of forking
Steps 1–4 into a separate repo, this one repo hosts an MCP server per BookMeBus
project: a target-agnostic `mcp_core/` (the factory + config/git/http helpers) and
one thin package per target under `mcp_targets/`. A fix to the shared plumbing then
benefits every target — no drift. (Rationale and trade-offs: DEVELOPING.md §5.)

**Extended (2026-11-16): targets are plugins, config is scoped.** Targets are now
discovered by convention — each exposes a `TARGET` (`mcp_core/plugin.py`) found by
`mcp_core/registry.py` — and run through one launcher, `polymcp <target>`
(`mcp_core/cli.py`). Adding a target is "drop a folder," no pyproject/core edit.
Config landed as a typed schema + a **source-agnostic `SettingsStore`**
(`mcp_core/settings.py`) scoped by a folder-derived prefix (`AVOCADO_*` /
`CM_MARKET_SERVER_*`), source swappable (env/memory/json; db-ready) and writable — pulling
Step 4 forward.

- [x] Prove the structure: `mcp_core.build_server(ctx)` + `mcp_targets/
      avocado` + `mcp_targets/cm_market_server`, the plugin contract + launcher, tests
      mirroring src. **Verified:** tests pass; `polymcp --list` shows both;
      both launch on stdio; each exposes the shared `health` tool (which reports
      identity); scoped settings proven (no cross-target var leak).
- [ ] As Steps 2–5 land in `mcp_core` + `mcp_targets/avocado`, give cm-market-server
      its real tools (its own repo path via `CM_MARKET_SERVER_PATH`, Spree +
      `spree_cm_commissioner` specifics, API base).
- **Verify:** `uv run pytest` green for all targets; `polymcp cm-market-server`
  reaches the same "green Step 2" against the cm-market-server repo that avocado does.
- **Note:** the dist name is already `polymcp`; keep the per-target **server
  names** Claude Code sees (`avocado-web`, `cm-market-server`).

---

### Open questions (resolve before the step that needs them)

- **Step 2:** is the git tag the canonical version, or does deploy use something
  else? CLAUDE.md says ECR images are "tagged from the latest git tag" — treat
  the tag as canonical unless a `VERSION`/release file appears.
- **Step 5:** which staging base URL and which single endpoint is safest to start
  with? Needs the `operator-tenant` `BASE_API` value / a staging app credential.
