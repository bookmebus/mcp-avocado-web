"""`basics` department — a couple of harmless demo tools.

Each department module exposes ONE `register(mcp, settings)` that attaches its
tools. This is the pattern every target follows; copy it for a real department.
Tool bodies stay thin — real logic would live in a service function, kept testable.
Reads use `settings.values` (typed); writes use `settings.set(...)`.
"""

from mcp.server.mcpserver import MCPServer

from mcp_core.settings import SettingsStore
from mcp_targets.demo.config import DemoSettings


def register(mcp: MCPServer, settings: SettingsStore[DemoSettings]) -> None:
    """Attach the demo tools to the given server, using the target's settings."""

    @mcp.tool()
    def echo(text: str) -> str:
        """Return `text` unchanged — a reachability check that takes an argument."""
        return text

    @mcp.tool()
    def greet(name: str) -> str:
        """Greet `name` using the configured greeting (DEMO_GREETING)."""
        return f"{settings.values.greeting}, {name}!"

    @mcp.tool()
    def set_greeting(greeting: str) -> str:
        """Change the greeting greet() uses (writes through the settings store)."""
        settings.set("greeting", greeting)  # validated + persisted to the overlay
        return f"greeting is now {settings.values.greeting!r}"
