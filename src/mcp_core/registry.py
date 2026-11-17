"""Discover target plugins by convention.

This is the ONE place that enumerates targets. It walks the `mcp_targets`
package and collects every subpackage that exposes a `TARGET` (a `TargetSpec`).
No hardcoded list: a new target is found the moment its folder exists.

Upgrade path: if targets ever ship as separate installed packages (or as
third-party plugins), swap this body for `importlib.metadata.entry_points()`
discovery. The `TargetSpec` contract and the launcher stay exactly the same.
"""

import importlib  # import a module at runtime from its name as a STRING
import pkgutil  # list the modules inside a package WITHOUT importing them
from dataclasses import dataclass

import mcp_targets  # the package whose folder we scan
from mcp_core.config import slug_from  # folder name -> CLI slug
from mcp_core.plugin import TargetSpec  # the type a real target must expose


@dataclass(frozen=True)
class Discovery:
    """The result of one discovery pass.

    `targets` maps slug -> spec for the usable targets. `errors` maps slug -> a
    short message for targets that FAILED to import — kept separate so one broken
    target can't hide (or crash) the healthy ones.
    """

    targets: dict[str, TargetSpec]
    errors: dict[str, str]


def discover_targets() -> Discovery:
    """Discover every target package under `mcp_targets/`, in isolation.

    A subpackage is a usable target only if it imports cleanly AND exposes a
    module-level `TARGET` that is a `TargetSpec`. An import failure is recorded in
    `errors` (keyed by the target's slug) instead of propagating, so `--list` and
    every other target keep working.
    """
    targets: dict[str, TargetSpec] = {}
    errors: dict[str, str] = {}

    # pkgutil.iter_modules lists what's inside mcp_targets/ without importing it.
    # Each pass gives one `info`, e.g. info.name='mcp_targets.demo', ispkg=True.
    for info in pkgutil.iter_modules(mcp_targets.__path__, f"{mcp_targets.__name__}."):
        if not info.ispkg:  # skip loose .py files; only subpackages are targets
            continue
        slug = slug_from(info.name)  # error key = the CLI slug, even if import fails

        # ISOLATE: a broken target (syntax/import error) is recorded, not raised,
        # so it can't take down discovery for the rest.
        try:
            module = importlib.import_module(info.name)
        except Exception as exc:  # catch ANYTHING: isolating a broken target is the point
            errors[slug] = f"{type(exc).__name__}: {exc}"
            continue

        spec = getattr(module, "TARGET", None)  # None if this package isn't a target
        if not isinstance(spec, TargetSpec):  # rejects None, or TARGET = 42
            continue
        if spec.name in targets:  # two folders claiming one slug
            errors[spec.name] = "duplicate slug (defined by more than one package)"
            continue
        targets[spec.name] = spec  # key by slug — what you type on the CLI

    return Discovery(targets, errors)
