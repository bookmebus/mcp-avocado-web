"""Source-agnostic settings for targets.

A target's config has two independent parts:

- **Schema** — which keys exist and their types: a plain pydantic `BaseModel`.
  Still typed, still validated.
- **Source** — where the values come from and go to: the process environment, an
  in-memory dict, a JSON file, a database, … behind the `SettingsSource` interface.

`SettingsStore` binds a schema to one or more sources and exposes **typed reads**
and **validated writes**, so a target never touches `os.environ` or a database
directly, and swapping the backing store is a one-line change. Reads prefer the
first source that has a key; writes go to the first *writable* source.

    class DemoSettings(BaseModel):
        greeting: str = "Hello"

    # read-only, env-backed:
    settings = env_store(DemoSettings, "demo")
    settings.values.greeting               # -> "Hello"  (typed, autocompletes)

    # writable: a memory overlay above env
    settings = env_store(DemoSettings, "demo", overlay=MemorySource())
    settings.set("greeting", "Hi")         # validated, persisted to the overlay
    settings.values.greeting               # -> "Hi"
"""

from __future__ import annotations

import json
import os

# ABC = "Abstract Base Class": tools for declaring an INTERFACE — a class that
# lists methods but can't be used on its own until a subclass fills them in.
#   - ABC: inherit from it to mark a class abstract (can't be instantiated directly).
#   - abstractmethod: decorate a method to REQUIRE every concrete subclass to
#     implement it; Python raises TypeError the moment you try to create a subclass
#     (or the base) that hasn't. (Ruby equivalent: raising NotImplementedError by
#     hand — but this is enforced at object creation, not only when called.)
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from dotenv import dotenv_values
from pydantic import BaseModel, TypeAdapter

from mcp_core.config import env_files, env_prefix

M = TypeVar("M", bound=BaseModel)


class ReadOnlySettings(RuntimeError):
    """Raised when writing to a store/source that has no writable backing."""


# --------------------------------------------------------------------------- #
# Sources — the swappable backends. Keys are fully-resolved names (already
# prefixed, e.g. "MY_APP_DB_URL"); values are strings, like the environment.
# The schema layer (SettingsStore) does the typing and validation.
# --------------------------------------------------------------------------- #
class SettingsSource(ABC):  # (ABC) => this is an interface; `SettingsSource()` is a TypeError
    """A string key -> string value store behind `get()` / `set()`."""

    writable: bool = False

    @abstractmethod  # every concrete source (Env/Memory/Json/Db) MUST implement get()
    def get(self, key: str) -> str | None:
        """Return the value for `key`, or None if this source doesn't have it."""

    # set() is NOT abstract: it has a working default (raise), so read-only sources
    # inherit it for free and only writable sources override it.
    def set(self, key: str, value: str) -> None:
        """Persist `key`. Read-only sources raise; writable ones override this."""
        raise ReadOnlySettings(f"{type(self).__name__} is read-only; cannot set {key!r}")


class EnvSource(SettingsSource):
    """Read-only: the process environment overlaid on a target's `.env` files.

    Precedence inside the source: real `os.environ` > later env file > earlier.
    `os.environ` is read live on each `get`; the files are read once at startup.
    An env var set to empty (`FOO=`) is a *present* value `""`, not "unset" — omit
    the var entirely to fall through to the schema default.
    """

    writable = False

    def __init__(self, files: tuple[Path, ...] = ()):
        self._file_values: dict[str, str] = {}
        for f in files:  # earlier files first; later ones override
            self._file_values.update({k: v for k, v in dotenv_values(f).items() if v is not None})

    def get(self, key: str) -> str | None:
        if key in os.environ:  # real env always wins over files
            return os.environ[key]
        return self._file_values.get(key)


class MemorySource(SettingsSource):
    """Read/write, in-process. Ideal for tests and runtime overrides."""

    writable = True

    def __init__(self, initial: dict[str, str] | None = None):
        self._data: dict[str, str] = dict(initial or {})

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value


class JsonFileSource(SettingsSource):
    """Read/write, persisted to a JSON file.

    A concrete durable store you can use today, and the template for a real
    `DbSource`: implement the same two methods against your table instead of a
    file. (Reads load the whole file — fine for small config, not a hot path.)
    """

    writable = True

    def __init__(self, path: Path):
        self._path = path

    def _load(self) -> dict[str, str]:
        try:
            return json.loads(self._path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get(self, key: str) -> str | None:
        return self._load().get(key)

    def set(self, key: str, value: str) -> None:
        data = self._load()
        data[key] = value
        self._path.write_text(json.dumps(data, indent=2, sort_keys=True))


# --------------------------------------------------------------------------- #
# Store — binds a typed schema to the sources above.
# --------------------------------------------------------------------------- #
class SettingsStore(Generic[M]):
    """Typed, source-agnostic settings for one target.

    `sources` are highest-precedence first: a read returns the first source that
    has the key. A write goes to the first *writable* source (and is validated
    against the schema first); if none is writable, `set` raises ReadOnlySettings.

    Read fields via `store.values` — the validated, **typed** model (autocompletes
    and type-checks) — or `store.get("field")` for dynamic access. Write with
    `store.set("field", value)`.
    """

    def __init__(self, schema: type[M], *sources: SettingsSource, prefix: str = ""):
        if not sources:
            raise ValueError("SettingsStore needs at least one source")
        self._schema = schema
        self._sources = sources
        self._prefix = prefix
        self._cache: M | None = None

    def _key(self, field: str) -> str:
        """Field name -> fully-resolved source key, e.g. 'db_url' -> 'MY_APP_DB_URL'."""
        return f"{self._prefix}{field.upper()}"

    def _raw(self) -> dict[str, str]:
        """Collect the raw string value for each schema field, by source precedence."""
        out: dict[str, str] = {}
        for field in self._schema.model_fields:
            key = self._key(field)
            for src in self._sources:  # highest precedence first
                val = src.get(key)
                if val is not None:
                    out[field] = val
                    break
        return out

    def load(self) -> M:
        """Build and validate the typed model from the current source values."""
        return self._schema(**self._raw())

    @property
    def values(self) -> M:
        """The validated model, cached. Call `reload()` or `set()` to refresh."""
        if self._cache is None:
            self._cache = self.load()
        return self._cache

    def reload(self) -> M:
        """Drop the cache and re-read from the sources (e.g. after env changes)."""
        self._cache = None
        return self.values

    def get(self, field: str) -> Any:
        """Read one field by NAME — the dynamic, string-keyed escape hatch.

        Prefer `store.values.<field>` for everyday reads: it's typed and
        autocompletes. Use this only when the field name is itself a variable.
        """
        return getattr(self.values, field)

    def set(self, field: str, value: Any) -> None:
        """Validate `value` against the field's type and persist it to a writable source.

        The wire form is a string (`str(value)`), to stay compatible with the
        environment, so `value` must be a scalar that round-trips: `None` is
        rejected (a string source has no way to represent "unset" — there is no
        delete), and lists/dicts aren't supported.
        """
        if field not in self._schema.model_fields:
            raise KeyError(f"{self._schema.__name__} has no field {field!r}")
        if value is None:
            raise ValueError(
                f"cannot set {field!r} to None: a string-backed source can't represent 'unset'"
            )
        writable = next((s for s in self._sources if s.writable), None)
        if writable is None:
            raise ReadOnlySettings(
                f"no writable source for {self._schema.__name__}; cannot set {field!r}"
            )
        # Validate/coerce ONLY this field (not the whole model), so a bad value
        # sitting in another field can't block this write, and we don't re-read
        # every source. Persist the normalized value as its string wire form.
        annotation = self._schema.model_fields[field].annotation
        if annotation is None:  # a defined pydantic field always has a type
            raise RuntimeError(f"field {field!r} has no type annotation")
        coerced = TypeAdapter(annotation).validate_python(value)
        writable.set(self._key(field), str(coerced))
        # Invalidate (don't assume the written value wins): a higher-precedence
        # source may still shadow it, so the next read recomputes by precedence.
        self._cache = None


def env_store(
    schema: type[M],
    slug: str,
    *,
    overlay: SettingsSource | None = None,
    overlay_wins: bool = True,
) -> SettingsStore[M]:
    """A store for `schema` backed by this slug's env + `.env` files.

    Read-only by default (env is read-only). Pass `overlay` — a `MemorySource`, a
    `JsonFileSource`, or a future `DbSource` — to make it writable. Writes always
    go to the overlay; `overlay_wins` decides READ precedence:

    - `True` (default): overlay > env. A runtime `set` shadows env, so the write
      visibly takes effect. Use for runtime-mutable settings (feature flags, a
      db-backed value you intend to change).
    - `False`: env > overlay. The environment stays authoritative; the overlay
      only fills keys env doesn't set (and still receives writes, which are
      visible only where env is unset). Use when ops-set env must not be
      overridden by a runtime write.
    """
    env = EnvSource(env_files(slug))
    if overlay is None:
        sources: tuple[SettingsSource, ...] = (env,)
    elif overlay_wins:
        sources = (overlay, env)
    else:
        sources = (env, overlay)
    return SettingsStore(schema, *sources, prefix=env_prefix(slug))
