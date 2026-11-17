# Publishing the framework (open-source)

`polymcp` (the framework) is reusable and names no specific target. This repo
also ships two **BookMeBus targets** as its working example. If you open-source
the framework on its own, keep the framework, drop the BookMeBus specifics, and
ship a generic example in their place.

## Keep — the reusable framework

- `src/mcp_core/` — factory, plugin contract (`plugin.py`), discovery
  (`registry.py`), launcher (`cli.py`), `config.py` (derivations), and the
  source-agnostic `settings.py` (`SettingsStore` + sources). Names no target.
- `src/mcp_targets/__init__.py` — the namespace (generic).
- `src/mcp_targets/demo/` + `tests/mcp_targets/demo/` + `.env.demo.example` — the
  BookMeBus-free example target. It demonstrates the whole framework and is what a
  reader copies to start their own; keep it.
- `tests/mcp_core/` — framework tests (factory, registry, launcher).
- `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `.vscode/`.
- `.claude/skills/plugin-target/` — the one framework-level skill.
- `DEVELOPING.md`, `ROADMAP.md` (trim BookMeBus-specific roadmap steps).

## Strip — BookMeBus-specific (private)

These describe internal projects/architecture; remove before publishing:

- `src/mcp_targets/avocado/`, `src/mcp_targets/cm_market_server/` (the brand
  strings live in each target's `meta.toml`, so they leave with the folder)
- `tests/mcp_targets/avocado/`, `tests/mcp_targets/cm_market_server/`
- `.env.avocado.example`, `.env.cm-market-server.example`
- `.claude/skills/db-access/`, `.claude/skills/departments/`,
  `.claude/skills/security/` — these are guidance for the BookMeBus targets
  (Rails DBs, `/api/v2`, department tools). The generic framework doesn't need them.
- Any BookMeBus wording left in `README.md` (the "Targets in this repo" note and
  the avocado/cm-market rows) and in `DEVELOPING.md`'s SOA/`/api/v2` examples.

## The example target is already here

`src/mcp_targets/demo/` is the neutral, BookMeBus-free target — kept (above), not
added. After stripping avocado/cm-market, `polymcp --list` still shows `demo`, so
the published repo demonstrates the framework end to end on its own. The
`plugin-target` skill walks a reader through adding their own, using `demo` as the
reference.

## Sanity check before publishing

The core must not name any target. From the repo root:

```bash
grep -rin "bookmebus\|avocado\|cm-market\|cm_market" src/mcp_core && echo "LEAK ^" || echo "core is clean"
```

Expect `core is clean`.
