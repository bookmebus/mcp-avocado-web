"""Shared, target-agnostic core of the framework.

Everything here is reused by every target server under `mcp_targets/` — the
server factory, the plugin contract + discovery, the launcher, and config
helpers. Target packages stay thin and import from here, so the plumbing is
written and tested ONCE. Nothing in this package names a specific target.

`__version__` below is the DISTRIBUTION version (the installable package, read by
pyproject's [tool.hatch.version]). Each target server carries its OWN
`__version__` — what its `health` tool reports — and the two are
deliberately independent: a target can ship a new version without re-versioning
the whole distribution.
"""

__version__ = "0.1.0"
