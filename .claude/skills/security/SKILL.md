---
name: security
description: Use BEFORE exposing any BookMeBus data through an MCP tool, or when handling DB credentials, secrets, env files, or passenger/payment (PII) data. Rules for the reads-from-DB / writes-through-API split, read-only DB users, SQL-injection safety, secrets in gitignored .env, PII minimization, and keeping local dev paths out of the repo.
---

# Security rules for the BookMeBus MCP servers

These servers can touch **real passenger and payment data** in avocado-web and
cm-market-server. Treat every tool as if it will be called with hostile input,
because an LLM will pass it arbitrary strings.

## 1. Reads from the DB, writes through the API

- **Reads** may query the Rails DB directly (see the `db-access` skill).
- **Writes must go through `/api/v2`, never raw SQL.** Writing directly skips
  Rails validations, callbacks, Sidekiq jobs, and the `spree_cm_commissioner`
  commission logic — you would silently create inconsistent data.

`/api/v2` is consumed by **shipped mobile binaries**: it's a public contract.
Add fields, never rename or remove them (from the workspace `CLAUDE.md`).

## 2. Least-privilege database user

Create a dedicated **read-only** user for the MCP. This is the real safety net:
even a buggy or jailbroken tool can't corrupt data.

```sql
-- MySQL (avocado-web), native-password auth to match the server policy
CREATE USER 'mcp_ro'@'%' IDENTIFIED WITH mysql_native_password BY '<strong-pass>';
GRANT SELECT ON avocado.* TO 'mcp_ro'@'%';
```
```sql
-- Postgres (cm-market-server)
CREATE ROLE mcp_ro LOGIN PASSWORD '<strong-pass>';
GRANT CONNECT ON DATABASE <db> TO mcp_ro;
GRANT USAGE ON SCHEMA public TO mcp_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_ro;
```
`SELECT`-only — no `INSERT`/`UPDATE`/`DELETE`/`DROP`.

## 3. SQL injection — parameterized queries only

Never build SQL with f-strings, `%`, `+`, or `.format()`. Use bound parameters.

```python
# WRONG — injectable:  text(f"... WHERE code = '{code}'")
# RIGHT:
conn.execute(text("... WHERE code = :code"), {"code": code})
```

## 4. Secrets stay in per-target .env files, never in the repo

- Config is **per target** and **scoped**: each target's `SettingsStore` reads
  only its prefix keys (`AVOCADO_*` / `CM_MARKET_SERVER_*`) from env +
  its own gitignored `.env.<target>` (plus an optional shared `.env`). A target's
  DB password and API secrets go in **its own** file only — and the prefix means
  one target can't even read another's vars. (See the `plugin-target` skill.)
- Only the `*.example` templates are committed, and they carry **placeholders
  only** (`/path/to/...`, `CHANGE_ME`, empty secrets).
- **Never log a DSN or secret.** Never echo it into a tool result.
- Never paste a real credential into a commit, a comment, or a message.

## 5. Minimize PII in tool output

Passenger emails/phones, auth tokens, and payment fields are PII. A tool should
`SELECT` only the columns it needs and return a shaped dict — don't `SELECT *`
and hand the model a row full of tokens. If a tool doesn't need the email, don't
fetch the email.

## 6. Keep local dev paths out of the repo

Don't bake absolute paths or usernames (`/Users/<you>/...`) into committed files.
Derive defaults from a file's own location or read them from `.env`. This repo
was already scrubbed once — don't reintroduce it.
