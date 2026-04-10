from __future__ import annotations

from pathlib import Path

from work_mcp.config import DB_TYPE_MYSQL, DB_TYPE_SQLSERVER, PROJECT_ROOT
from work_mcp.setup import (
    DATABASE_CHOICE_BY_NUMBER,
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

PLUGIN_DATABASE = "database"
PLUGIN_LOG_SEARCH = "log_search"
PLUGIN_DINGTALK = "dingtalk"
YES_NO_CHOICES = {
    "1": False,
    "2": True,
}
DEFAULT_DISABLE_CHOICE = "1"
DEFAULT_DATABASE_CHOICE = "1"


def prompt_choice(prompt: str, choices: dict[str, object], default_choice: str) -> object:
    str_choices = {str(k): v for k, v in choices.items()}
    while True:
        raw_value = input(f"{prompt} [press Enter for {default_choice}]: ").strip()
        selected = raw_value or str(default_choice)
        if selected in str_choices:
            return str_choices[selected]
        print("输入无效，请输入给定选项编号。")


def prompt_keep_existing(label: str, current_value: str, *, secret_field: str = "") -> bool:
    shown_value = current_value_label(secret_field, current_value) if secret_field else current_value
    print(f"当前{label}: {shown_value}")
    choice = prompt_choice(
        "是否保留当前值？\n1. 保留（默认）\n2. 重新输入\n请输入选项",
        {"1": True, "2": False},
        "1",
    )
    return bool(choice)


def prompt_text(
    label: str,
    *,
    existing_value: str = "",
    default_value: str = "",
    validator,
    allow_empty: bool = False,
    secret_field: str = "",
) -> object:
    if existing_value and prompt_keep_existing(label, existing_value, secret_field=secret_field):
        return validator(existing_value) if not allow_empty else existing_value

    while True:
        suffix = f" [press Enter for {default_value}]" if default_value else ""
        raw_value = input(f"{label}{suffix}: ")
        candidate = raw_value.strip()
        if not candidate and default_value:
            candidate = default_value
        if not candidate and allow_empty:
            return ""
        try:
            return validator(candidate)
        except RuntimeError as exc:
            print(f"输入不合法: {exc}")


def prompt_yes_no(label: str, *, current_enabled: bool | None = None) -> bool:
    if current_enabled is not None:
        print(f"当前{label}: {'已开启' if current_enabled else '未开启'}")
    print(f"是否开启{label}？")
    print("1. 不开启（默认）")
    print("2. 开启")
    selected = prompt_choice("请输入选项", YES_NO_CHOICES, DEFAULT_DISABLE_CHOICE)
    return bool(selected)


def prompt_database_type(existing_env: dict[str, str]) -> str:
    existing_db_type = existing_env.get("DB_TYPE", "").strip().lower()
    if existing_db_type in {DB_TYPE_MYSQL, DB_TYPE_SQLSERVER}:
        choice_number = "1" if existing_db_type == DB_TYPE_MYSQL else "2"
        print(f"当前数据库类型: {existing_db_type}")
        if prompt_keep_existing("数据库类型", existing_db_type):
            return existing_db_type
    else:
        choice_number = DEFAULT_DATABASE_CHOICE

    print("请选择数据库类型：")
    print("1. mysql（默认）")
    print("2. sqlserver")
    selected = prompt_choice("请输入选项", DATABASE_CHOICE_BY_NUMBER, choice_number)
    return str(selected)


def prompt_sqlserver_trust_cert(existing_env: dict[str, str]) -> bool:
    existing_value = existing_env.get("DB_TRUST_SERVER_CERTIFICATE", "").strip()
    if existing_value and prompt_keep_existing(
        "是否信任服务器证书", existing_value, secret_field=""
    ):
        return parse_bool_text(existing_value)

    print("是否信任服务器证书？")
    print("1. 否（默认）")
    print("2. 是")
    selected = prompt_choice("请输入选项", YES_NO_CHOICES, DEFAULT_DISABLE_CHOICE)
    return bool(selected)


def enabled_plugins_from_yaml(yaml_values: dict) -> set[str]:
    plugins = yaml_values.get("plugins", {})
    if not isinstance(plugins, dict):
        return set()
    raw_enabled = plugins.get("enabled", [])
    if not isinstance(raw_enabled, list):
        return set()
    return {str(item).strip() for item in raw_enabled if str(item).strip()}


def collect_database_answers(existing_env: dict[str, str]) -> dict[str, object]:
    print("\n[数据库配置]")
    db_type = prompt_database_type(existing_env)
    port_default = str(default_port_for_db(db_type))

    return {
        "db_type": db_type,
        "host": str(
            prompt_text(
                "数据库地址是什么",
                existing_value=existing_env.get("DB_HOST", ""),
                validator=lambda value: validate_required_text(value, "DB_HOST"),
            )
        ),
        "port": int(
            prompt_text(
                "数据库端口是多少",
                existing_value=existing_env.get("DB_PORT", ""),
                default_value=port_default,
                validator=lambda value: validate_port(value, "DB_PORT"),
            )
        ),
        "user": str(
            prompt_text(
                "数据库用户名是什么",
                existing_value=existing_env.get("DB_USER", ""),
                validator=lambda value: validate_required_text(value, "DB_USER"),
            )
        ),
        "password": str(
            prompt_text(
                "数据库密码是什么",
                existing_value=existing_env.get("DB_PASSWORD", ""),
                validator=lambda value: validate_required_text(value, "DB_PASSWORD"),
                secret_field="DB_PASSWORD",
            )
        ),
        "database_name": str(
            prompt_text(
                "默认连接的数据库名是什么",
                existing_value=existing_env.get("DB_NAME", ""),
                default_value="master",
                validator=lambda value: validate_required_text(value, "DB_NAME"),
            )
        ),
        "connect_timeout_seconds": int(
            prompt_text(
                "数据库连接超时时间（秒）是多少",
                existing_value=existing_env.get("DB_CONNECT_TIMEOUT_SECONDS", ""),
                default_value="5",
                validator=lambda value: validate_positive_int(
                    value, "DB_CONNECT_TIMEOUT_SECONDS"
                ),
            )
        ),
    }


def collect_sqlserver_answers(existing_env: dict[str, str], db_type: str) -> dict[str, object]:
    if db_type != DB_TYPE_SQLSERVER:
        return {
            "driver": "",
            "trust_server_certificate": False,
        }

    return {
        "driver": str(
            prompt_text(
                "SQL Server ODBC Driver 名称是什么",
                existing_value=existing_env.get("DB_DRIVER", ""),
                default_value=default_driver_for_db(db_type),
                validator=validate_sqlserver_driver,
            )
        ),
        "trust_server_certificate": prompt_sqlserver_trust_cert(existing_env),
    }


def collect_answers(project_root: Path = PROJECT_ROOT) -> SetupAnswers:
    env_values = parse_env_file(env_file_path(project_root))
    yaml_values = load_existing_yaml(project_root / "config.yaml")
    existing_plugins = enabled_plugins_from_yaml(yaml_values)

    print("开始初始化配置。")
    print("请先选择要开启的模块；直接回车表示不开启。")

    enable_database = prompt_yes_no(
        "database", current_enabled=PLUGIN_DATABASE in existing_plugins
    )
    enable_log_search = prompt_yes_no(
        "log_search", current_enabled=PLUGIN_LOG_SEARCH in existing_plugins
    )
    enable_dingtalk = prompt_yes_no(
        "dingtalk", current_enabled=PLUGIN_DINGTALK in existing_plugins
    )

    database_answers: dict[str, object] = {
        "db_type": DB_TYPE_MYSQL,
        "host": "",
        "port": default_port_for_db(DB_TYPE_MYSQL),
        "user": "",
        "password": "",
        "database_name": "",
        "driver": "",
        "trust_server_certificate": False,
        "connect_timeout_seconds": 5,
    }
    if enable_database:
        database_answers.update(collect_database_answers(env_values))
        database_answers.update(
            collect_sqlserver_answers(env_values, str(database_answers["db_type"]))
        )

    log_base_dir = ""
    if enable_log_search:
        print("\n[日志搜索配置]")
        log_base_dir = str(
            prompt_text(
                "日志根目录的绝对路径是什么",
                existing_value=_existing_log_base_dir(yaml_values),
                validator=validate_log_base_dir,
            )
        )

    dingtalk_webhook_url = ""
    dingtalk_secret = ""
    if enable_dingtalk:
        print("\n[钉钉配置]")
        dingtalk_webhook_url = str(
            prompt_text(
                "钉钉 webhook 地址是什么",
                existing_value=env_values.get("DINGTALK_WEBHOOK_URL", ""),
                validator=lambda value: validate_required_text(
                    value, "DINGTALK_WEBHOOK_URL"
                ),
            )
        )
        dingtalk_secret = str(
            prompt_text(
                "钉钉加签 secret 是什么（可留空）",
                existing_value=env_values.get("DINGTALK_SECRET", ""),
                allow_empty=True,
                validator=lambda value: value,
                secret_field="DINGTALK_SECRET",
            )
        )

    return SetupAnswers(
        enable_database=enable_database,
        db_type=str(database_answers["db_type"]),
        host=str(database_answers["host"]),
        port=int(database_answers["port"]),
        user=str(database_answers["user"]),
        password=str(database_answers["password"]),
        database_name=str(database_answers["database_name"]),
        driver=str(database_answers["driver"]),
        trust_server_certificate=bool(database_answers["trust_server_certificate"]),
        connect_timeout_seconds=int(database_answers["connect_timeout_seconds"]),
        enable_log_search=enable_log_search,
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
        raise SystemExit(f"错误: {exc}") from None
    except KeyboardInterrupt:
        print("\n已取消初始化。")
        raise SystemExit(1) from None

    existing_env = parse_env_file(env_path)
    existing_yaml = load_existing_yaml(yaml_path)

    write_env_file(env_path, build_updated_env(existing_env, answers))
    write_yaml_file(yaml_path, build_updated_yaml(existing_yaml, answers))

    print("\n开始执行配置检查...")
    results = diagnose(project_root)
    for result in results:
        print(f"[{result.level}] {result.message}")

    if has_errors(results):
        raise SystemExit(
            "配置已保存，但校验未通过。请重新运行 `make init` 修正配置。"
        )

    print("配置保存成功。")
    print("运行 `uv run work-mcp` 启动服务。")


if __name__ == "__main__":
    main()
