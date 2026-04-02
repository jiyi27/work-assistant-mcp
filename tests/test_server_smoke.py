from __future__ import annotations

import asyncio
from unittest.mock import patch

from work_assistant_mcp.server import mcp


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def read(self) -> bytes:
        return b'{"errcode":0,"errmsg":"ok"}'


def test_list_tools_includes_dingtalk_send_markdown() -> None:
    tools = asyncio.run(mcp.list_tools())

    assert [tool.name for tool in tools] == ["dingtalk_send_markdown"]


def test_dingtalk_send_markdown_returns_structured_result() -> None:
    with patch("work_assistant_mcp.tools.dingtalk.urlopen", return_value=FakeResponse()):
        _, structured = asyncio.run(
            mcp.call_tool(
                "dingtalk_send_markdown",
                {"title": "Smoke Test", "markdown": "hello"},
            )
        )

    assert structured == {"ok": True, "errcode": 0, "errmsg": "ok"}
