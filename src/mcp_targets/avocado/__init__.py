"""avocado-web target: MCP server for the Rails 4.2 core service.

`TARGET` is this plugin's descriptor: the launcher discovers it (see
`mcp_core.registry`) and runs `build()`. Version / name / description are display
metadata that load from `.env.avocado` (see config.py) and override at runtime;
the values here are the `--list` defaults. `__version__` re-exports the single
distribution version, so no per-target version literal lives in code.
"""

from mcp_core import __version__
from mcp_core.config import slug_from
from mcp_core.plugin import TargetSpec
from mcp_targets.avocado.config import DEFAULT_DESCRIPTION, DEFAULT_SERVER_NAME
from mcp_targets.avocado.server import build

TARGET = TargetSpec(
    name=slug_from(__package__),  # 'avocado', derived from the folder name
    version=__version__,  # dist version; AVOCADO_VERSION overrides at runtime
    description=DEFAULT_DESCRIPTION,  # `--list` default; AVOCADO_DESCRIPTION overrides
    build=build,
    server_name=DEFAULT_SERVER_NAME,  # `--list` default; AVOCADO_SERVER_NAME overrides
)
