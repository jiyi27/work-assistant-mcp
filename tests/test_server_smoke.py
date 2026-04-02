from __future__ import annotations

import asyncio
import json
from pathlib import Path
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


def test_dingtalk_send_markdown_writes_success_log(tmp_path: Path) -> None:
    with patch("work_assistant_mcp.tools.dingtalk.urlopen", return_value=FakeResponse()):
        with patch.dict(
            "os.environ",
            {
                "DINGTALK_WEBHOOK_URL": "https://example.invalid/webhook",
                "WORK_ASSISTANT_LOG_DIR": str(tmp_path),
                "WORK_ASSISTANT_LOG_LEVEL": "info",
            },
            clear=False,
        ):
            _, structured = asyncio.run(
                mcp.call_tool(
                    "dingtalk_send_markdown",
                    {"title": "Smoke Test", "markdown": "hello"},
                )
            )

    assert structured == {"ok": True, "errcode": 0, "errmsg": "ok"}
    files = list(tmp_path.glob("*.info.log"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
    assert record["topic"] == "dingtalk.sent"
