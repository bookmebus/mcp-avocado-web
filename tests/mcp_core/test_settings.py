"""The source-agnostic settings store. Mirrors src/mcp_core/settings.py."""

from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from mcp_core.settings import (
    EnvSource,
    JsonFileSource,
    MemorySource,
    ReadOnlySettings,
    SettingsStore,
    env_store,
)


class Demo(BaseModel):
    greeting: str = "Hello"
    retries: int = 3
    home: Path = Path("/tmp")


def store(*sources: object, prefix: str = "DEMO_") -> SettingsStore[Demo]:
    return SettingsStore(Demo, *sources, prefix=prefix)  # type: ignore[arg-type]


# --- sources -------------------------------------------------------------- #
def test_memory_source_read_write() -> None:
    m = MemorySource()
    assert m.get("X") is None
    m.set("X", "1")
    assert m.get("X") == "1" and m.writable is True


def test_env_source_env_wins_over_file(tmp_path, monkeypatch) -> None:
    f = tmp_path / ".env.demo"
    f.write_text("DEMO_GREETING=from-file\n")
    src = EnvSource((f,))
    assert src.get("DEMO_GREETING") == "from-file"  # from the file
    monkeypatch.setenv("DEMO_GREETING", "from-env")
    assert src.get("DEMO_GREETING") == "from-env"  # real env wins over file
    assert src.get("DEMO_MISSING") is None and src.writable is False


def test_json_file_source_persists(tmp_path) -> None:
    p = tmp_path / "s.json"
    JsonFileSource(p).set("DEMO_GREETING", "saved")
    assert JsonFileSource(p).get("DEMO_GREETING") == "saved"  # new instance, same file


# --- store: typed reads --------------------------------------------------- #
def test_store_typed_read_and_coercion(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_RETRIES", "7")  # a string in the source...
    s = store(EnvSource())
    assert s.values.greeting == "Hello"  # default (not in env)
    assert s.values.retries == 7 and isinstance(s.values.retries, int)  # coerced by schema
    assert s.get("greeting") == "Hello"  # get() is the dynamic read


# --- store: validated writes --------------------------------------------- #
def test_write_validates_and_persists_to_overlay() -> None:
    overlay = MemorySource()
    s = store(overlay, EnvSource())
    s.set("greeting", "Hi")
    assert s.values.greeting == "Hi"  # cache refreshed
    assert overlay.get("DEMO_GREETING") == "Hi"  # persisted to the writable source
    with pytest.raises(ValidationError):  # bad type rejected before persisting
        s.set("retries", "not-an-int")


def test_overlay_takes_read_precedence_over_env(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_GREETING", "from-env")
    s = store(MemorySource({"DEMO_GREETING": "from-overlay"}), EnvSource())
    assert s.values.greeting == "from-overlay"


def test_readonly_store_rejects_write() -> None:
    with pytest.raises(ReadOnlySettings):
        store(EnvSource()).set("greeting", "nope")  # env-only = read-only


def test_unknown_field_rejected() -> None:
    with pytest.raises(KeyError):
        store(MemorySource()).set("nope", "x")


def test_set_none_is_rejected() -> None:
    # A string-backed source can't represent "unset", so None must not silently
    # become the literal "None".
    with pytest.raises(ValueError, match="None"):
        store(MemorySource()).set("greeting", None)


def test_set_validates_only_the_target_field() -> None:
    # A bad value already in the environment for ANOTHER field must not block a
    # valid write (set() validates just the field being written).
    import os

    os.environ["DEMO_RETRIES"] = "not-an-int"
    try:
        overlay = MemorySource()
        store(overlay, EnvSource()).set("greeting", "Hi")  # must not raise
        assert overlay.get("DEMO_GREETING") == "Hi"
    finally:
        del os.environ["DEMO_RETRIES"]


# --- the env_store convenience ------------------------------------------- #
def test_env_store_readonly_by_default_writable_with_overlay() -> None:
    assert isinstance(env_store(Demo, "demo"), SettingsStore)
    with pytest.raises(ReadOnlySettings):
        env_store(Demo, "demo").set("greeting", "x")
    rw = env_store(Demo, "demo", overlay=MemorySource())
    rw.set("greeting", "x")
    assert rw.values.greeting == "x"


def test_overlay_wins_false_keeps_env_authoritative(monkeypatch) -> None:
    # env > overlay: a real env var is NOT overridden by a runtime write, but the
    # overlay still fills keys env doesn't set.
    monkeypatch.setenv("DEMO_GREETING", "from-env")
    s = env_store(Demo, "demo", overlay=MemorySource(), overlay_wins=False)
    s.set("greeting", "ignored")  # write lands in overlay...
    assert s.values.greeting == "from-env"  # ...but env still wins on read
    s.set("home", "/tmp/x")  # a key env does NOT set
    assert str(s.values.home) == "/tmp/x"  # overlay fills it
