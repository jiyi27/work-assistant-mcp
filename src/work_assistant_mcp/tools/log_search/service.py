from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles

from ...config import LogSearchSettings
from ...hints import required_param_hint
from .constants import CONTEXT_LINES, MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB, MAX_LISTED_ENTRIES, MAX_RESULTS
from .strings import (
    HINT_FILE_NOT_FOUND,
    HINT_LIST_LOG_FILES_SUCCESS,
    HINT_NO_RESULTS,
    HINT_PATH_OUTSIDE_BASE,
    HINT_TRUNCATED,
    TOOL_LIST_LOG_FILES,
    TOOL_SEARCH_LOG,
    file_too_large_hint,
)


class LogSearchService:
    def __init__(self, settings: LogSearchSettings) -> None:
        self._settings = settings
        self._base = Path(settings.log_base_dir).resolve()

    def _safe_resolve(self, relative: str) -> Path | None:
        """Resolve a path relative to log_base_dir. Returns None if outside base."""
        target = (self._base / relative).resolve()
        try:
            target.relative_to(self._base)
        except ValueError:
            return None
        return target

    def list_files(self, path: str = "") -> dict[str, Any]:
        relative = path.strip()
        if relative in {".", "./"}:
            relative = ""
        if relative.endswith("/"):
            relative = relative.rstrip("/")

        target = self._safe_resolve(relative)
        if target is None:
            return {
                "success": False,
                "error_type": "path_outside_base",
                "hint": HINT_PATH_OUTSIDE_BASE,
            }
        if not target.exists():
            return {
                "success": False,
                "error_type": "path_not_found",
                "hint": (
                    f"Path '{relative or '.'}' does not exist. "
                    f"Call {TOOL_LIST_LOG_FILES} with an existing directory path."
                ),
            }
        if not target.is_dir():
            return {
                "success": False,
                "error_type": "not_a_directory",
                "hint": (
                    f"'{relative}' is a file, not a directory. "
                    f"Use {TOOL_SEARCH_LOG} to search files."
                ),
            }

        entries_with_mtime: list[tuple[float, dict[str, Any]]] = []
        for child in target.iterdir():
            rel = str(child.relative_to(self._base))
            stat = child.stat()
            entry: dict[str, Any] = {
                "name": child.name,
                "path": rel,
                "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
            if child.is_dir():
                entry["type"] = "dir"
            else:
                entry["type"] = "file"
                entry["size_kb"] = round(stat.st_size / 1024, 1)
            entries_with_mtime.append((stat.st_mtime, entry))

        entries_with_mtime.sort(key=lambda item: (-item[0], item[1]["name"]))
        entries = [entry for _, entry in entries_with_mtime[:MAX_LISTED_ENTRIES]]

        return {
            "success": True,
            "path": relative,
            "entries": entries,
            "hint": HINT_LIST_LOG_FILES_SUCCESS,
        }

    async def search(self, file_path: str, query: str) -> dict[str, Any]:
        file_path = file_path.strip()
        query = query.strip()

        if not file_path:
            return {
                "success": False,
                "error_type": "invalid_input",
                "hint": required_param_hint("file_path"),
            }
        if not query:
            return {
                "success": False,
                "error_type": "invalid_input",
                "hint": required_param_hint("query"),
            }

        target = self._safe_resolve(file_path)
        if target is None:
            return {
                "success": False,
                "error_type": "path_outside_base",
                "hint": HINT_PATH_OUTSIDE_BASE,
            }
        if not target.exists():
            return {
                "success": False,
                "error_type": "file_not_found",
                "hint": f"File '{file_path}' does not exist. {HINT_FILE_NOT_FOUND}",
            }
        # P1: reject directories — agent may pass a dir path from list_log_files
        if target.is_dir():
            return {
                "success": False,
                "error_type": "not_a_file",
                "hint": (
                    f"'{file_path}' is a directory. "
                    f"Call {TOOL_LIST_LOG_FILES} to list its contents."
                ),
            }
        file_size = target.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            return {
                "success": False,
                "error_type": "file_too_large",
                "hint": file_too_large_hint(MAX_FILE_SIZE_MB),
            }

        async with aiofiles.open(target, encoding="utf-8", errors="replace") as f:
            lines = (await f.read()).splitlines()

        lowered_query = query.lower()
        results: list[dict[str, Any]] = []
        truncated = False
        for line_index in range(len(lines) - 1, -1, -1):
            line = lines[line_index]
            if lowered_query not in line.lower():
                continue
            if len(results) >= MAX_RESULTS:
                truncated = True
                break

            results.append({
                "line_no": line_index + 1,
                "match": line,
                "pre_context": lines[max(0, line_index - CONTEXT_LINES):line_index],
                "post_context": lines[line_index + 1:line_index + 1 + CONTEXT_LINES],
            })

        if not results:
            return {
                "success": True,
                "results": [],
                "hint": HINT_NO_RESULTS,
            }

        results.sort(key=lambda item: item["line_no"])
        response: dict[str, Any] = {"success": True, "results": results}
        if truncated:
            response["truncated"] = True
            response["hint"] = HINT_TRUNCATED
        return response
