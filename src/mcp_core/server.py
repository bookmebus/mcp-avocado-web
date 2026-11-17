"""The shared MCP server factory.

Every target server is built by calling `build_server(ctx, settings.values)`. It
creates the MCPServer object and registers the tools that ALL targets share
(currently just `health`). The target then adds its own tools with `@mcp.tool()`.
This is the "shared core" of the multi-target design: the wiring lives here once;
`mcp_targets/*` only compose it.

`health` is a RESERVED tool name — don't register another tool called `health`.
"""

from dataclasses import replace

from mcp.server.mcpserver import MCPServer

from mcp_core.plugin import BuildContext, TargetIdentity


def build_server(ctx: BuildContext, meta: TargetIdentity | None = None) -> MCPServer:
    """Create an MCP server from a `BuildContext`, with the shared tools registered.

    `meta` (a target's live settings) overrides the context's name / version /
    description, so values configured in `.env.<target>` reach the MCP handshake
    and the `health` tool — identity is content, loaded from config, not literals.

    Returns the MCPServer, ready for the target to attach its own tools and `run()`.
    """
    if meta is not None:
        ctx = replace(
            ctx,
            name=meta.server_name,
            version=meta.version,
            description=meta.description,
        )

    mcp = MCPServer(ctx.name, version=ctx.version)

    @mcp.tool()
    def health() -> dict:
        """Report server identity and health: name, version, description, status.

        A reachability check that exercises the tool path end to end — distinct
        from the MCP handshake, and the single place identity is exposed, so
        targets don't each hand-write one.
        """
        return {
            "server": ctx.name,
            "version": ctx.version,
            "description": ctx.description,
            "status": "ok",
        }

    return mcp
