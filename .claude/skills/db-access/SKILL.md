---
name: db-access
description: Use when adding or changing an MCP tool that READS from a BookMeBus Rails database — avocado-web (MySQL 8.4) or cm-market-server (Postgres). Covers the shared engine factory, read-only querying with SQLAlchemy Core, parameterized queries, LIMIT/pagination, and connection pooling. Pair with the `security` skill before exposing any row.
---

# Connecting MCP tools to the Rails databases

This project's MCP servers may read directly from the BookMeBus Rails DBs.
**Reads come from the DB; writes do NOT — writes go through `/api/v2`** (see the
`security` skill for why). This skill is only about safe reads.

## The databases

A target is **not** pinned to one database. The relationship is many-to-many: a
target may own its own DB, **share** a DB with another target, or read from
**several**. Today's defaults:

| Database | Engine | Driver (add at Step 5) | DSN scheme | Used by |
| --- | --- | --- | --- | --- |
| avocado | **MySQL 8.4.9** | `pymysql` | `mysql+pymysql://user:pass@host:3306/avocado` | avocado-web |
| cm_market | **Postgres 18** | `psycopg[binary]` | `postgresql+psycopg://user:pass@host:5432/db` | cm-market-server |

Think of a **DSN as the unit**, not the target. Two targets that need the same
database point at the **same DSN** and automatically share one connection pool
(see the factory below) — nothing special to wire. A new target that reuses
avocado's MySQL just reads the same `AVOCADO_WEB_DSN` env var.

> **avocado auth note:** its MySQL runs with `--authentication-policy=mysql_native_password`
> (the Rails `mysql2` client can't do `caching_sha2_password`). So your read-only
> user uses native password and `pymysql` connects with no `cryptography` needed
> for the handshake. Do NOT "fix" this by switching the user to caching_sha2.

Add the drivers only when you actually wire a DB tool (Roadmap Step 5):
`uv add sqlalchemy pymysql "psycopg[binary]"`.

## Where things live (follows the existing layout)

- `src/mcp_core/db.py` — the **shared** engine factory, written once. Target-agnostic;
  it caches one pool per DSN, so sharing a DB across targets is free (see below).
- `src/mcp_targets/<target>/config.py` — a typed pydantic schema bound by
  `env_store` to a scoped `SettingsStore` (see the `plugin-target` skill) with a
  typed DSN field. Never
  hard-code a DSN. The field name + prefix form the env var (e.g. prefix
  `AVOCADO_` + field `web_dsn` → `AVOCADO_WEB_DSN`). Two targets sharing a DB read
  the **same** DSN value into their own scoped field; a target using several has
  several fields.
- `src/mcp_targets/<target>/tools/<department>.py` — the query functions
  (see the `departments` skill for how tools are grouped).

## The engine factory (the one pattern to reuse)

An Engine holds a **connection pool** — make it once per process, not per call.
Think ActiveRecord's pool: created at boot, reused for every query.

```python
# src/mcp_core/db.py
"""Shared, read-only-intended database engines for the MCP targets."""
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@lru_cache(maxsize=None)          # same DSN -> same Engine -> one pool per process
def make_engine(dsn: str) -> Engine:
    return create_engine(
        dsn,
        pool_pre_ping=True,       # verify a connection is alive before using it
        pool_recycle=1800,        # drop connections older than 30 min
        future=True,
    )
```

## Querying safely (SQLAlchemy Core, not the ORM)

Use plain SQL with **bound parameters** — never f-strings or `+` into SQL
(the `security` skill explains the injection risk). `:name` is a safe placeholder.

```python
from sqlalchemy import text

def find_reservation(engine, code: str) -> dict | None:
    sql = text(
        "SELECT id, code, status, created_at "
        "FROM reservations WHERE code = :code LIMIT 1"   # always bound, always LIMIT
    )
    with engine.connect() as conn:                        # connect = read-only use
        row = conn.execute(sql, {"code": code}).mappings().first()
    return dict(row) if row else None
```

## Rules for every DB tool

1. **Always `LIMIT`.** An LLM tool that returns 10k rows blows the context
   window and the bill. Cap results; paginate with `LIMIT`/`OFFSET` or a keyset.
2. **Bound parameters only** (`:name` + a dict). No string interpolation.
3. **`engine.connect()`, not `begin()`** for reads — no transaction/commit needed.
4. **Read the Rails schema first.** `db/schema.rb` in each repo is the source of
   truth for table/column names and types. Don't guess column names.
5. **Return shaped dicts**, not raw rows — pick the columns the tool needs so the
   model (and the person reading it) gets a clean, small payload.
6. **Don't select PII you don't need** (emails, tokens, payment fields). See the
   `security` skill.

MySQL 8 is stricter than 5.7 (`ONLY_FULL_GROUP_BY` is on): every non-aggregated
column in a `SELECT` with `GROUP BY` must appear in the `GROUP BY`.
