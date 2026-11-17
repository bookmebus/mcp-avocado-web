"""demo target: a minimal, dependency-free example server.

It names no external system — it exists to demonstrate the framework (the plugin
contract, the launcher, scoped config, the department pattern) and to be the
example that remains if the app-specific targets are removed. Copy this folder to
start a real target. Version / name / description load from `.env.demo`;
`__version__` re-exports the single distribution version.
"""

from mcp_core import __version__
from mcp_core.config import slug_from
from mcp_core.plugin import TargetSpec
from mcp_targets.demo.config import DEFAULT_DESCRIPTION
from mcp_targets.demo.server import build

TARGET = TargetSpec(
    name=slug_from(__package__),  # 'demo', derived from the folder name
    version=__version__,  # dist version; DEMO_VERSION overrides at runtime
    description=DEFAULT_DESCRIPTION,  # `--list` default; DEMO_DESCRIPTION overrides
    build=build,
    # server_name omitted → the MCP client sees the slug ("demo")
)
