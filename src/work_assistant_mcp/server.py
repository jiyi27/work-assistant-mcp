from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import Settings, get_settings
from .logger import configure as configure_logger
from .tools import TOOL_REGISTRY


def create_mcp(settings: Settings) -> FastMCP:
    """Build and return a configured FastMCP instance with the enabled tools registered."""
    mcp = FastMCP(
        name=settings.server_name,
        instructions=settings.server_instructions,
    )
    for tool_name in settings.enabled_tools:
        register_fn = TOOL_REGISTRY.get(tool_name)
        if register_fn is None:
            known = ", ".join(sorted(TOOL_REGISTRY))
            raise RuntimeError(
                f"Unknown tool '{tool_name}' in config.yaml. "
                f"Available tools: {known}"
            )
        register_fn(mcp)
    return mcp


def main() -> None:
    """Entry point for the MCP server."""
    settings = get_settings()
    configure_logger(log_dir=settings.log_dir, level=settings.log_level)
    mcp = create_mcp(settings)
    mcp.run()
