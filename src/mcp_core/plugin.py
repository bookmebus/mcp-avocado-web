"""The target plugin contract.

A *target* is a plugin: a self-contained package under `mcp_targets/` that
describes itself with a `TARGET` value and knows how to build its own server.
The launcher (`mcp_core.cli`) discovers these without the core ever naming a
target — so you add a target by dropping a folder, not by editing the core.

Identity lives HERE, once. The launcher hands `build()` a `BuildContext` (not loose
positional args), so `build()` never hardcodes name/version — and the contract can
gain inputs later without changing every target's signature.

Every target package's `__init__.py` must expose:

    TARGET = TargetSpec(name="myapp", version=__version__, description="...", build=build)
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from mcp.server.mcpserver import MCPServer


class TargetIdentity(Protocol):
    """The live, env-overridable identity a target's settings expose to `build_server`.

    Any object with these three attributes satisfies it (a target's settings model
    does). `build_server` reads them so `.env`-configured identity reaches the MCP
    handshake and the `health` tool.
    """

    server_name: str
    version: str
    description: str


@dataclass(frozen=True)
class BuildContext:
    """What the launcher passes to a target's `build()` (and on to `build_server`).

    A single object rather than positional args, so the build path can gain inputs
    over time (capabilities, a logger, shared clients) without a signature change
    rippling through every target.

    Attributes:
        name: the client-facing server name (the spec's `mcp_name`).
        version: this server's version.
        description: the one-line description (also what the shared `health` tool
            reports, so targets don't each hand-write an identity tool).
    """

    name: str
    version: str
    description: str


@dataclass(frozen=True)
class TargetSpec:
    """What a target plugin publishes about itself — its single source of identity.

    Attributes:
        name: the plugin's slug. Used on the CLI (`polymcp <name>`) and as the
            suffix of the env file it loads (`.env.<name>`). Keep it stable; it is
            a public handle.
        version: this server's version — reported by its `health` tool and in the
            MCP handshake. Pass the package's `__version__`.
        description: one line shown by `polymcp --list`.
        build: builds the server. Receives a `BuildContext` and returns a
            ready-to-run MCPServer, so it never repeats the name/version itself.
        server_name: the name an MCP client sees in the handshake. Defaults to
            `name`; set it only when it must differ from the slug (e.g. slug
            `app` → server `app-web`).
    """

    name: str
    version: str
    description: str
    build: Callable[[BuildContext], MCPServer]
    server_name: str | None = None

    @property
    def mcp_name(self) -> str:
        """The client-facing server name (falls back to the slug)."""
        return self.server_name or self.name

    def create(self) -> MCPServer:
        """Build this target's server with its own declared identity."""
        return self.build(
            BuildContext(
                name=self.mcp_name,
                version=self.version,
                description=self.description,
            )
        )
