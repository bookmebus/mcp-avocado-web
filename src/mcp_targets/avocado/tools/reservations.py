"""Reservations department — booking and trip lookups.

The team that owns reservations adds tools HERE, not in server.py.
`register(mcp, settings)` is the one hook server.py calls. Tool bodies below are
PLACEHOLDERS: they return illustrative strings so the wiring is provable now; the
real /api/v2 calls land in ROADMAP Step 5 (using `settings` for the API base/DSN,
their logic kept thin here and pushed into a service module).
"""

from mcp.server.mcpserver import MCPServer

from mcp_core.settings import SettingsStore
from mcp_targets.avocado.config import AvocadoSettings


def register(mcp: MCPServer, settings: SettingsStore[AvocadoSettings]) -> None:
    """Attach the reservations tools to the given server."""

    @mcp.tool()
    def find_reservation(code: str) -> str:
        """Look up a reservation by its booking code (e.g. 'BMB-10231')."""
        return f"[placeholder] reservation {code} — wire to /api/v2 in Step 5"

    @mcp.tool()
    def trips_today() -> str:
        """List today's departing trips."""
        return "[placeholder] today's departing trips — wire to /api/v2 in Step 5"
