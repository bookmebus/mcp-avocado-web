"""The launcher lists targets and rejects bad input. Mirrors src/mcp_core/cli.py.

We never call `main()` with a real target here — that would start a stdio server
and block. We test the paths that return without running: --list and errors.
"""

import mcp_core.cli as cli
from mcp_core.cli import main
from mcp_core.registry import Discovery


def _patch_discovery(monkeypatch, targets, errors) -> None:
    monkeypatch.setattr(cli, "discover_targets", lambda: Discovery(targets, errors))


def test_list_shows_both_targets(capsys) -> None:
    code = main(["--list"])
    out = capsys.readouterr().out
    assert code == 0
    assert "avocado" in out
    assert "cm-market-server" in out


def test_no_target_is_a_usage_error(capsys) -> None:
    code = main([])
    assert code == 2
    assert "no target given" in capsys.readouterr().err


def test_unknown_target_is_rejected(capsys) -> None:
    code = main(["does-not-exist"])
    assert code == 2
    assert "unknown target" in capsys.readouterr().err


def test_list_reports_broken_targets(monkeypatch, capsys) -> None:
    # A target that failed to import is surfaced on --list, not hidden.
    _patch_discovery(monkeypatch, targets={}, errors={"broke": "ImportError: boom"})
    code = main(["--list"])
    assert code == 0
    assert "broke" in capsys.readouterr().err  # reported to stderr


def test_running_a_broken_target_reports_why(monkeypatch, capsys) -> None:
    _patch_discovery(monkeypatch, targets={}, errors={"broke": "ImportError: boom"})
    code = main(["broke"])
    assert code == 2
    err = capsys.readouterr().err
    assert "failed to load" in err and "boom" in err
