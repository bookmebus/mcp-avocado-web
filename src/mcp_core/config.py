"""Shared configuration derivations used by targets.

Each target derives its **slug** from its folder, and from the slug its **env
prefix** and **env-file paths**. These are pure functions of the folder name. The
typed, source-agnostic settings machinery that uses them lives in
`mcp_core.settings`.
"""

import tomllib
from pathlib import Path
from typing import Any

# Repo root: this file is src/mcp_core/config.py, so parents[2] is the repo root.
# Env files (.env, .env.<slug>) live here, NOT inside src/, so they are never
# packaged into the wheel.
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_meta(module_file: str) -> dict[str, Any]:
    """Read a target's committed `meta.toml` (sibling of `module_file`).

    Display metadata (description, server_name) is CONTENT, so it lives in plain
    text next to the target — never as a brand/string literal in `.py`. Call with
    `__file__` from the target's `config.py`. Env vars still override at runtime.
    """
    path = Path(module_file).resolve().parent / "meta.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def slug_from(package: str | None) -> str:
    """Derive a target's slug from its package dunder name (`__package__`).

    Takes the last dotted part and turns underscores into hyphens — Python
    packages can't contain hyphens, but CLI slugs and env files conventionally do:

        'mcp_targets.my_app' -> 'my-app'
        'mcp_targets.demo'   -> 'demo'

    `__package__` is typed Optional (it's unset for a top-level script), but it is
    always set inside a package, so we guard and fail loudly if misused.
    """
    if not package:
        raise ValueError("slug_from needs a package name — pass __package__ from inside a package")
    return package.rsplit(".", 1)[-1].replace("_", "-")


def env_prefix(slug: str) -> str:
    """Env-var prefix for a slug: upper-cased, hyphens as underscores, trailing `_`.

    'file-store' -> 'FILE_STORE_'
    'demo'       -> 'DEMO_'
    """
    return slug.upper().replace("-", "_") + "_"


def env_files(slug: str) -> tuple[Path, ...]:
    """This target's env files, LOWEST precedence first: shared `.env`, then `.env.<slug>`."""
    return (REPO_ROOT / ".env", REPO_ROOT / f".env.{slug}")
