from __future__ import annotations

from pathlib import Path

from work_mcp.config import DB_TYPE_MYSQL, DB_TYPE_SQLSERVER, PROJECT_ROOT
from work_mcp.setup import (
    DATABASE_CHOICE_BY_NUMBER,
    NO_YES_CHOICES,
    SetupAnswers,
    build_updated_env,
    build_updated_yaml,
    current_value_label,
    default_driver_for_db,
    default_port_for_db,
    diagnose,
    env_file_path,
    has_errors,
    load_existing_yaml,
    parse_bool_text,
    parse_env_file,
    validate_log_base_dir,
    validate_port,
    validate_positive_int,
    validate_required_text,
    validate_sqlserver_driver,
    write_env_file,
    write_yaml_file,
)

DEFAULT_ENABLE_DINGTALK_CHOICE = "1"
DEFAULT_DATABASE_CHOICE = "1"


def prompt_choice(prompt: str, choices: dict[str, object], default_choice: str) -> object:
    while True:
        raw_value = input(f"{prompt} [{default_choice}]: ").strip()
        selected = raw_value or default_choice
        if selected in choices:
            return choices[selected]
        print("Invalid input. Please enter one of the listed options.")


def prompt_keep_existing(field_name: str, current_value: str) -> bool:
    print(f"{field_name} current value: {current_value_label(field_name, current_value)}")
    choice = prompt_choice(
        "Keep the current value?\n1. Yes (default)\n2. No\nEnter choice",
        {"1": True, "2": False},
        "1",
    )
    return bool(choice)


def prompt_text(
    field_name: str,
    *,
    existing_value: str = "",
    default_value: str = "",
    validator,
    allow_empty: bool = False,
) -> object:
    if existing_value and prompt_keep_existing(field_name, existing_value):
        return validator(existing_value) if not allow_empty else existing_value

    while True:
        suffix = f" [{default_value}]" if default_value else ""
        raw_value = input(f"{field_name}{suffix}: ")
        candidate = raw_value.strip()
        if not candidate and default_value:
            candidate = default_value
        if not candidate and allow_empty:
            return ""
        try:
            return validator(candidate)
        except RuntimeError as exc:
            print(f"Invalid input: {exc}")


def prompt_database_type(existing_env: dict[str, str]) -> str:
    existing_db_type = existing_env.get("DB_TYPE", "").strip().lower()
    if existing_db_type in {DB_TYPE_MYSQL, DB_TYPE_SQLSERVER}:
        choice_number = "1" if existing_db_type == DB_TYPE_MYSQL else "2"
        print(f"DB_TYPE current value: {existing_db_type}")
        if prompt_keep_existing("DB_TYPE", existing_db_type):
            return existing_db_type
    else:
        choice_number = DEFAULT_DATABASE_CHOICE

    print("Select database type:")
    print("1. mysql (default)")
    print("2. sqlserver")
    selected = prompt_choice("Enter choice", DATABASE_CHOICE_BY_NUMBER, choice_number)
    return str(selected)


def prompt_enable_dingtalk(existing_yaml: dict, existing_env: dict[str, str]) -> bool:
    enabled_plugins = existing_yaml.get("plugins", {})
    current_enabled = False
    if isinstance(enabled_plugins, dict):
        raw_enabled = enabled_plugins.get("enabled", [])
        if isinstance(raw_enabled, list):
            current_enabled = "dingtalk" in {str(item).strip() for item in raw_enabled}

    if current_enabled:
        print("dingtalk current value: enabled")
        if prompt_keep_existing("dingtalk plugin", "enabled"):
            return True
    elif existing_env.get("DINGTALK_WEBHOOK_URL", "").strip():
        print("dingtalk current value: disabled")

    print("Enable dingtalk plugin:")
    print("1. No (default)")
    print("2. Yes")
    selected = prompt_choice("Enter choice", NO_YES_CHOICES, DEFAULT_ENABLE_DINGTALK_CHOICE)
    return bool(selected)


def collect_answers(project_root: Path = PROJECT_ROOT) -> SetupAnswers:
    env_values = parse_env_file(env_file_path(project_root))
    yaml_values = load_existing_yaml(project_root / "config.yaml")

    db_type = prompt_database_type(env_values)
    port_default = str(default_port_for_db(db_type))

    host = str(
        prompt_text(
            "DB_HOST",
            existing_value=env_values.get("DB_HOST", ""),
            validator=lambda value: validate_required_text(value, "DB_HOST"),
        )
    )
    port = int(
        prompt_text(
            "DB_PORT",
            existing_value=env_values.get("DB_PORT", ""),
            default_value=port_default,
            validator=lambda value: validate_port(value, "DB_PORT"),
        )
    )
    user = str(
        prompt_text(
            "DB_USER",
            existing_value=env_values.get("DB_USER", ""),
            validator=lambda value: validate_required_text(value, "DB_USER"),
        )
    )
    password = str(
        prompt_text(
            "DB_PASSWORD",
            existing_value=env_values.get("DB_PASSWORD", ""),
            validator=lambda value: validate_required_text(value, "DB_PASSWORD"),
        )
    )
    database_name = str(
        prompt_text(
            "DB_NAME",
            existing_value=env_values.get("DB_NAME", ""),
            validator=lambda value: validate_required_text(value, "DB_NAME"),
        )
    )

    if db_type == DB_TYPE_SQLSERVER:
        driver = str(
            prompt_text(
                "DB_DRIVER",
                existing_value=env_values.get("DB_DRIVER", ""),
                default_value=default_driver_for_db(db_type),
                validator=validate_sqlserver_driver,
            )
        )
        trust_server_certificate = bool(
            prompt_text(
                "DB_TRUST_SERVER_CERTIFICATE",
                existing_value=env_values.get("DB_TRUST_SERVER_CERTIFICATE", ""),
                default_value="false",
                validator=parse_bool_text,
            )
        )
    else:
        driver = ""
        trust_server_certificate = False

    connect_timeout_seconds = int(
        prompt_text(
            "DB_CONNECT_TIMEOUT_SECONDS",
            existing_value=env_values.get("DB_CONNECT_TIMEOUT_SECONDS", ""),
            default_value="5",
            validator=lambda value: validate_positive_int(value, "DB_CONNECT_TIMEOUT_SECONDS"),
        )
    )
    log_base_dir = str(
        prompt_text(
            "log_search.log_base_dir",
            existing_value=_existing_log_base_dir(yaml_values),
            validator=validate_log_base_dir,
        )
    )

    enable_dingtalk = prompt_enable_dingtalk(yaml_values, env_values)
    if enable_dingtalk:
        dingtalk_webhook_url = str(
            prompt_text(
                "DINGTALK_WEBHOOK_URL",
                existing_value=env_values.get("DINGTALK_WEBHOOK_URL", ""),
                validator=lambda value: validate_required_text(value, "DINGTALK_WEBHOOK_URL"),
            )
        )
        dingtalk_secret = str(
            prompt_text(
                "DINGTALK_SECRET",
                existing_value=env_values.get("DINGTALK_SECRET", ""),
                allow_empty=True,
                validator=lambda value: value,
            )
        )
    else:
        dingtalk_webhook_url = ""
        dingtalk_secret = ""

    return SetupAnswers(
        db_type=db_type,
        host=host,
        port=port,
        user=user,
        password=password,
        database_name=database_name,
        driver=driver,
        trust_server_certificate=trust_server_certificate,
        connect_timeout_seconds=connect_timeout_seconds,
        log_base_dir=log_base_dir,
        enable_dingtalk=enable_dingtalk,
        dingtalk_webhook_url=dingtalk_webhook_url,
        dingtalk_secret=dingtalk_secret,
    )


def _existing_log_base_dir(yaml_values: dict) -> str:
    log_search = yaml_values.get("log_search")
    if not isinstance(log_search, dict):
        return ""
    return str(log_search.get("log_base_dir", "")).strip()


def main() -> None:
    project_root = PROJECT_ROOT
    env_path = env_file_path(project_root)
    yaml_path = project_root / "config.yaml"

    try:
        answers = collect_answers(project_root)
    except RuntimeError as exc:
        raise SystemExit(f"Error: {exc}") from None
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        raise SystemExit(1) from None

    existing_env = parse_env_file(env_path)
    existing_yaml = load_existing_yaml(yaml_path)

    write_env_file(env_path, build_updated_env(existing_env, answers))
    write_yaml_file(yaml_path, build_updated_yaml(existing_yaml, answers))

    print("\nRunning diagnostics...")
    results = diagnose(project_root)
    for result in results:
        print(f"[{result.level}] {result.message}")

    if has_errors(results):
        raise SystemExit(
            "Configuration saved, but validation failed. Re-run `make init` to update the incorrect values."
        )

    print("Configuration saved successfully.")
    print("Run `uv run work-mcp` to start the server.")


if __name__ == "__main__":
    main()
