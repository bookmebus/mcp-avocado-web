"""Finance department — payments and settlement.

Same shape as every department module: one `register(mcp, settings)` hook. A
different team can own this file without ever touching reservations.py or
server.py. Placeholder bodies until Step 5.
"""

from mcp.server.mcpserver import MCPServer

from mcp_core.settings import SettingsStore
from mcp_targets.avocado.config import AvocadoSettings


def register(mcp: MCPServer, settings: SettingsStore[AvocadoSettings]) -> None:
    """Attach the finance tools to the given server."""

    @mcp.tool()
    def payment_status(reservation_code: str) -> str:
        """Return the payment status for a reservation (paid / pending / refunded)."""
        return f"[placeholder] payment status for {reservation_code} — Step 5"
