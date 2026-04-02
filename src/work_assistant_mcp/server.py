from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import get_settings
from .logger import configure as configure_logger
from .tools.dingtalk import register_dingtalk_tools

mcp = FastMCP(
    name="work-assistant-mcp",
    instructions="A work-focused MCP server with notification tools for local agents.",
)

register_dingtalk_tools(mcp)


def main() -> None:
    """Entry point for the MCP server."""
    settings = get_settings()
    configure_logger(log_dir=settings.log_dir, level=settings.log_level)
    mcp.run()
