# avocado-mcp roadmap

Small, traceable steps. **Each step ships one capability and at least one test
that proves it.** Don't start a step until the previous step's tests are green.
The end goal is a pattern clean enough to **replicate into the commissioner
monorepo** — so every step notes what carries over vs. what is avocado-specific.

Legend: `[x]` done · `[ ]` todo · each step lists its **Verify** gate.

---

## Step 1 — Scaffold + self-version `[x]`

Prove the plumbing before touching avocado-web.

- [x] uv project, `src/avocado_mcp` package, `__version__` single source of truth
- [x] `MCPServer` (MCP Python SDK v2) exposing `get_version` (server's own version)
- [x] pytest smoke tests: constant well-formed → function → tool registered
- [x] arm64 Python pin (native `cryptography` wheel; see README for the why)
- **Verify:** `uv run pytest` → 3 passed; `uv run avocado-mcp` starts on stdio.
- **Replicable:** everything here. This is the template skeleton.

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
  reusable idea. Commissioner would point `AVOCADO_WEB_PATH` at its own repo.

## Step 3 — Project facts resource `[ ]`

Move from "a tool" to "the server knows the project."

- [ ] An MCP **resource** (e.g. `avocado://project/info`) exposing stack facts
      from CLAUDE.md / Gemfile.lock: Rails 4.2.8, Ruby 2.3.8, default branch
      `develop`, remote `bookmebus/avocado`.
- [ ] Decide verified-vs-derived provenance for each fact (read live vs. pinned).
- **Verify:** resource lists; values match the repo; test asserts the schema.

## Step 4 — Config & packaging hardening `[ ]`

- [ ] Centralize settings (pydantic-settings or a small dataclass) so repo path,
      and future API base URLs, have one home.
- [ ] `ruff` lint + format; add to the test command.
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

## Step 7 — Replicate to commissioner `[ ]`

- [ ] Extract Steps 1–4 into a copyable template (rename package, repchange
      config defaults). Document the diff: what is generic vs. avocado-specific.
- **Verify:** fresh `commissioner-mcp` reaches "green Step 2" against its repo.

---

### Open questions (resolve before the step that needs them)

- **Step 2:** is the git tag the canonical version, or does deploy use something
  else? CLAUDE.md says ECR images are "tagged from the latest git tag" — treat
  the tag as canonical unless a `VERSION`/release file appears.
- **Step 5:** which staging base URL and which single endpoint is safest to start
  with? Needs the `operator-tenant` `BASE_API` value / a staging app credential.
