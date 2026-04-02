from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mcp.server.fastmcp import FastMCP

from ..config import get_settings
from ..logger import configure as configure_logger
from ..logger import error, info


def register_dingtalk_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def dingtalk_send_markdown(title: str, markdown: str) -> dict[str, Any]:
        """Send a formatted notification to the DingTalk group.

        Use this to report task progress, completion, errors, or any update
        that the user or team should be aware of.
        """
        title = title.strip()
        markdown = markdown.strip()
        if not title:
            error("dingtalk.validation_failed", {"field": "title"})
            raise RuntimeError("`title` must not be empty.")
        if not markdown:
            error("dingtalk.validation_failed", {"field": "markdown"})
            raise RuntimeError("`markdown` must not be empty.")

        settings = get_settings()
        configure_logger(log_dir=settings.log_dir, level=settings.log_level)
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": markdown,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            settings.dingtalk_webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=10) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            error(
                "dingtalk.request_failed",
                {"status_code": exc.code, "response_body": error_body},
                exc=exc,
            )
            raise RuntimeError(
                f"DingTalk webhook request failed with HTTP {exc.code}: {error_body}"
            ) from exc
        except URLError as exc:
            error("dingtalk.network_failed", {"reason": str(exc.reason)}, exc=exc)
            raise RuntimeError(f"Failed to reach DingTalk webhook: {exc.reason}") from exc

        result = json.loads(response_body)
        if result.get("errcode") != 0:
            error(
                "dingtalk.upstream_error",
                {
                    "errcode": result.get("errcode"),
                    "errmsg": result.get("errmsg", ""),
                },
            )
            raise RuntimeError(
                "DingTalk webhook returned an error: "
                f"{result.get('errcode')} {result.get('errmsg', '')}"
            )

        info(
            "dingtalk.sent",
            {
                "title": title,
                "errcode": result.get("errcode"),
                "errmsg": result.get("errmsg"),
            },
        )
        return {
            "ok": True,
            "errcode": result.get("errcode"),
            "errmsg": result.get("errmsg"),
        }
