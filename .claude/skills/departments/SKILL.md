---
name: departments
description: Use when adding MCP tools to a target and deciding where they go. BookMeBus MCP tools are grouped by department/domain (reservations, finance, ops, ...) — one module per department exposing a register(mcp, settings) function, composed in the target's server.py. Keep tool bodies thin and push real logic into a service layer.
---

# Organizing tools by department

A target (e.g. avocado) grows many tools for different departments and people.
Don't pile them all into `server.py`. Group them by **department/domain**, one
module each, so the file you open maps to the team whose work it serves.

## The structure (already used by the avocado target)

```
src/mcp_targets/avocado/
├── server.py            # composition root: build_server(...) + register each department
├── config.py            # this target's DSN / repo-path env vars
└── tools/
    ├── reservations.py  # find_reservation, trips_today
    ├── finance.py       # payment_status
    └── <department>.py  # add a new module when a new domain appears
```

## The contract: each module exposes `register(mcp, settings)`

Every department module defines **one** `register(mcp, settings)` function that
attaches its tools. `settings` is the target's `SettingsStore` (read typed values
via `settings.values.<field>`; write via `settings.set(...)`). `server.py` calls
each one. Adding a department = add a file + one `register` line; you never edit
the others (DRY, no merge conflicts).

```python
# tools/reservations.py
from mcp_core.settings import SettingsStore
from mcp_targets.avocado.config import AvocadoSettings

def register(mcp: MCPServer, settings: SettingsStore[AvocadoSettings]) -> None:
    @mcp.tool()
    def find_reservation(code: str) -> dict:
        """Look up one reservation by its code."""
        # thin: validate input, call the service (settings.values.api_base_url), shape result
        ...
```
```python
# server.py
from mcp_targets.avocado.tools import reservations, finance

def build(ctx):
    mcp = build_server(ctx)
    settings = make_settings()      # constructed here, not at import
    reservations.register(mcp, settings)   # one line per department
    finance.register(mcp, settings)
    return mcp
```

## Rules

1. **One department = one module** under `tools/`. Name it after the domain
   (`reservations`, `finance`, `ticketing`), not a person.
2. **`register(mcp, settings)` is the only public function** a module exposes to `server.py`.
3. **Keep tool bodies thin.** A tool validates input, calls a service function,
   and shapes the result. Real query/business logic lives in a service layer
   (SOA) — not inline in the decorator — so it's testable without MCP.
4. **Mirror in tests.** `tests/mcp_targets/<target>/tools/test_<department>.py`
   mirrors each module (the project's test layout mirrors `src/`).
5. **Split when a module gets crowded**, not before. Start a new department
   module when a domain clearly separates, not for every single tool.

See `db-access` for how a department's query functions reach the DB, and
`security` for what a tool may return.
