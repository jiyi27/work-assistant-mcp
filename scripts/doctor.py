from __future__ import annotations

from work_mcp.config import PROJECT_ROOT
from work_mcp.setup import diagnose, has_errors


def main() -> None:
    results = diagnose(PROJECT_ROOT)
    for result in results:
        print(f"[{result.level}] {result.message}")
    if has_errors(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
