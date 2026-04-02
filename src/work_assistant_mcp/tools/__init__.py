"""Tool registry — maps tool names (as used in config.yaml) to register functions."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from .dingtalk import register_dingtalk_tools

TOOL_REGISTRY: dict[str, Callable[[FastMCP], None]] = {
    "dingtalk": register_dingtalk_tools,
}
