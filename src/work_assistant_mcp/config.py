from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ENV_FILE_NAME = ".env"
YAML_CONFIG_FILE = "config.yaml"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_LEVELS = frozenset({"debug", "info", "warning", "error"})


@dataclass(frozen=True)
class Settings:
    # sensitive — loaded from .env / environment
    dingtalk_webhook_url: str
    dingtalk_secret: str | None
    # non-sensitive — loaded from config.yaml (env can override)
    log_dir: Path
    log_level: str
    server_name: str
    server_instructions: str
    enabled_tools: tuple[str, ...]


def load_env_file(env_path: Path | None = None) -> None:
    """Load key/value pairs from a local .env file without extra dependencies."""
    path = env_path or PROJECT_ROOT / ENV_FILE_NAME
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or key in os.environ:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ[key] = value


def load_yaml_config(yaml_path: Path | None = None) -> dict[str, Any]:
    """Load non-sensitive configuration from config.yaml."""
    path = yaml_path or PROJECT_ROOT / YAML_CONFIG_FILE
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_settings() -> Settings:
    load_env_file()
    yaml_cfg = load_yaml_config()

    # sensitive values — only from environment
    webhook_url = os.getenv("DINGTALK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise RuntimeError(
            "Missing DINGTALK_WEBHOOK_URL. Configure it in the environment or .env."
        )
    dingtalk_secret = os.getenv("DINGTALK_SECRET", "").strip() or None

    # non-sensitive values — env overrides yaml, yaml overrides defaults
    yaml_logging = yaml_cfg.get("logging", {})
    log_dir_raw = (
        os.getenv("WORK_ASSISTANT_LOG_DIR", "").strip()
        or yaml_logging.get("dir", "logs")
    )
    log_level = (
        os.getenv("WORK_ASSISTANT_LOG_LEVEL", "").strip().lower()
        or str(yaml_logging.get("level", "info")).lower()
    )
    if log_level not in LOG_LEVELS:
        valid_levels = ", ".join(sorted(LOG_LEVELS))
        raise RuntimeError(
            "Invalid WORK_ASSISTANT_LOG_LEVEL. "
            f"Expected one of: {valid_levels}."
        )

    yaml_server = yaml_cfg.get("server", {})
    server_name = yaml_server.get("name", "work-assistant-mcp")
    server_instructions = yaml_server.get("instructions", "")

    yaml_tools = yaml_cfg.get("tools", {})
    enabled_tools = tuple(yaml_tools.get("enabled", []))

    return Settings(
        dingtalk_webhook_url=webhook_url,
        dingtalk_secret=dingtalk_secret,
        log_dir=Path(log_dir_raw),
        log_level=log_level,
        server_name=server_name,
        server_instructions=server_instructions,
        enabled_tools=enabled_tools,
    )
