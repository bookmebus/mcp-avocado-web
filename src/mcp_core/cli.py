"""`polymcp` — the single launcher console script.

    polymcp --list         list every target this repo provides, then exit
    polymcp <target>       run that target on stdio

One script for all targets. Adding a target needs NO change here or in
pyproject: it is discovered from `mcp_targets/` (see `mcp_core.registry`).

Register a target with an MCP client by naming it after the launcher, e.g.:
    claude mcp add my-service -- uv --directory "$REPO" run polymcp my-service
"""

import argparse
import sys

from mcp_core.plugin import TargetSpec
from mcp_core.registry import discover_targets


def _print_targets(targets: dict[str, TargetSpec], stream) -> None:
    for name in sorted(targets):
        print(f"  {name}\t{targets[name].description}", file=stream)


def _print_errors(errors: dict[str, str], stream) -> None:
    for slug in sorted(errors):
        print(f"  ! {slug}\t(failed to load: {errors[slug]})", file=stream)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `polymcp` console script."""
    disc = discover_targets()

    parser = argparse.ArgumentParser(
        prog="polymcp",
        description="Run an MCP target server on stdio.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="which target to run; omit with --list to see all",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list available targets and exit",
    )
    args = parser.parse_args(argv)

    if args.list:
        _print_targets(disc.targets, sys.stdout)
        _print_errors(disc.errors, sys.stderr)  # broken targets are reported, not hidden
        return 0

    if args.target is None:
        print("error: no target given. Available targets:", file=sys.stderr)
        _print_targets(disc.targets, sys.stderr)
        return 2

    spec = disc.targets.get(args.target)
    if spec is None:
        if args.target in disc.errors:  # named a target that exists but failed to import
            print(
                f"error: target {args.target!r} failed to load: {disc.errors[args.target]}",
                file=sys.stderr,
            )
        else:
            print(f"error: unknown target {args.target!r}. Available targets:", file=sys.stderr)
            _print_targets(disc.targets, sys.stderr)
        return 2

    spec.create().run()  # build with the target's declared identity; stdio transport
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
