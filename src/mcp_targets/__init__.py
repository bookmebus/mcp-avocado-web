"""Namespace for per-target MCP servers — one subpackage per target project.

Each subpackage is a self-contained **plugin**: it imports the shared `mcp_core`,
declares its own scoped settings, registers its own tools, and exposes a `TARGET`
(a `mcp_core.plugin.TargetSpec`) describing itself and how to `build()` its server.

The launcher (`mcp_core.cli`, the `polymcp` script) discovers these by
walking this package (`mcp_core.registry`), so adding a target means dropping a
new subpackage here — nothing in the core or pyproject changes.
"""
