from __future__ import annotations

from ...hints import STOP_AND_NOTIFY_USER_INSTRUCTION

# Tool names — single source of truth used in registrations and cross-tool hints.
TOOL_LIST_LOG_FILES = "list_log_files"
TOOL_SEARCH_LOG = "search_log"

# Tool descriptions
LIST_LOG_FILES_DESCRIPTION = f"""\
List one level of files and subdirectories under the log root or a relative log path.

Use this to navigate the log directory tree and identify which file to search.
Start with path="" to see the log root, then drill into subdirectories as needed.
Each file entry includes its path, which can be passed directly to {TOOL_SEARCH_LOG}.
"""

SEARCH_LOG_DESCRIPTION = f"""\
Search a single log file for lines containing a query string and return matching lines with context.

Use this after {TOOL_LIST_LOG_FILES} to search a specific file. Provide a known identifier
such as a request ID, trace ID, error message, or status code.
"""

# Hints returned inside tool responses to guide the calling agent.
HINT_LIST_LOG_FILES_SUCCESS = (
    f"The result shows one level of the log directory tree for the returned path. "
    f"Continue calling {TOOL_LIST_LOG_FILES} with a directory path to drill down. "
    f"Use {TOOL_SEARCH_LOG} only after you identify a file to search."
)

HINT_PATH_OUTSIDE_BASE = (
    "The path resolves outside the configured log directory. "
    f"{STOP_AND_NOTIFY_USER_INSTRUCTION}"
)

HINT_NO_RESULTS = (
    f"No matching lines found. "
    f"Try a different query, or call {TOOL_LIST_LOG_FILES} to check which files are available."
)
