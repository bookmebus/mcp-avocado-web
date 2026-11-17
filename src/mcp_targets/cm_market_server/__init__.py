"""cm-market-server target: MCP server for the Spree marketplace.

cm-market-server is the Spree app built on the commission gem
(`spree_cm_commissioner`). `TARGET` is this plugin's descriptor, discovered by the
launcher (see `mcp_core.registry`). Version / name / description are display
metadata that load from `.env.cm-market-server`; the value here is the `--list`
default. `__version__` re-exports the single distribution version.
"""

from mcp_core import __version__
from mcp_core.config import slug_from
from mcp_core.plugin import TargetSpec
from mcp_targets.cm_market_server.config import DEFAULT_DESCRIPTION
from mcp_targets.cm_market_server.server import build

TARGET = TargetSpec(
    name=slug_from(__package__),  # 'cm-market-server', from folder 'cm_market_server'
    version=__version__,  # dist version; CM_MARKET_SERVER_VERSION overrides at runtime
    description=DEFAULT_DESCRIPTION,  # `--list` default; CM_MARKET_SERVER_DESCRIPTION overrides
    build=build,
)
