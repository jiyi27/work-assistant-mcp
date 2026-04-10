# init_config.py 重构方案

## 背景

当前 `scripts/init_config.py` 需要支持三个新特性：

1. SSL 证书信任字段去掉交互，直接写 `False`
2. 运行环境判断：先问本地还是远程，远程自动开启数据库和日志，其他不开启
3. 已有配置保护：检测到配置文件时先询问是否修改，默认不修改直接退出

在加这些特性之前，有一个结构性不一致需要先修复。

---

## 现有问题

### 插件配置收集不一致

| 插件 | 当前方式 |
|------|---------|
| `database` | `collect_database_answers()` 独立函数 |
| `jira` | `collect_jira_answers()` 独立函数 |
| `log_search` | 直接内联在 `collect_answers()` 中 |
| `dingtalk` | 直接内联在 `collect_answers()` 中 |

`collect_answers()` 目前同时承担"选插件"、"收集各插件配置"、"组装结果"三件事，
其中 log_search 和 dingtalk 的配置逻辑散落在主流程里，导致函数体过长，也让后续加分支变难。

### 默认值初始化不统一

database 和 jira 都用了预声明 dict 再 update 的模式，但 dingtalk 直接用裸变量，风格不一致。

---

## 重构目标

提取两个缺失的收集函数，让 `collect_answers()` 变成纯粹的三段式：

```
选择插件（enable_* 布尔值）
  ↓
按需收集各插件配置（collect_*_answers）
  ↓
组装 SetupAnswers 返回
```

加入新特性后，整体流程变为：

```
检测配置文件是否存在 → 已存在则询问是否修改 → 否则退出
  ↓
询问运行环境（本地 / 远程服务器）
  ↓
确定各插件的 enable_* 值
  - 远程：database=True, log_search=True, dingtalk=False, jira=False（自动，不询问）
  - 本地：逐个询问（现有流程）
  ↓
按需收集各插件配置（collect_*_answers，仅 enable=True 的插件）
  ↓
组装 SetupAnswers 写文件
```

---

## 具体改动

### 1. 提取 `collect_log_search_answers()`

从 `collect_answers()` 中抽出，与 database/jira 的函数风格保持一致：

```python
def collect_log_search_answers(yaml_values: dict) -> dict[str, str]:
    print("\n[日志搜索配置]")
    return {
        "log_base_dir": str(
            prompt_text(
                "日志根目录的绝对路径是什么",
                existing_value=_existing_log_base_dir(yaml_values),
                validator=validate_log_base_dir,
            )
        ),
    }
```

### 2. 提取 `collect_dingtalk_answers()`

同上：

```python
def collect_dingtalk_answers(existing_env: dict[str, str]) -> dict[str, str]:
    print("\n[钉钉配置]")
    return {
        "dingtalk_webhook_url": str(
            prompt_text(
                "钉钉 webhook 地址是什么",
                existing_value=existing_env.get("DINGTALK_WEBHOOK_URL", ""),
                validator=lambda value: validate_required_text(value, "DINGTALK_WEBHOOK_URL"),
            )
        ),
        "dingtalk_secret": str(
            prompt_text(
                "钉钉加签 secret 是什么（可留空）",
                existing_value=existing_env.get("DINGTALK_SECRET", ""),
                allow_empty=True,
                validator=lambda value: value,
                secret_field="DINGTALK_SECRET",
            )
        ),
    }
```

### 3. 去掉 `prompt_sqlserver_trust_cert()`，直接写 `False`

`collect_sqlserver_answers()` 中的 `trust_server_certificate` 字段不再交互，固定返回 `False`：

```python
def collect_sqlserver_answers(existing_env: dict[str, str], db_type: str) -> dict[str, object]:
    if db_type != DB_TYPE_SQLSERVER:
        return {"driver": "", "trust_server_certificate": False}
    return {
        "driver": str(
            prompt_text(
                "SQL Server ODBC Driver 名称是什么",
                existing_value=existing_env.get("DB_DRIVER", ""),
                default_value=default_driver_for_db(db_type),
                validator=validate_sqlserver_driver,
            )
        ),
        "trust_server_certificate": False,
    }
```

`prompt_sqlserver_trust_cert()` 函数随之删除。

### 4. 新增 `prompt_environment_type()`

```python
ENV_TYPE_REMOTE = "remote"
ENV_TYPE_LOCAL = "local"

def prompt_environment_type() -> str:
    print()
    print("当前是什么运行环境？")
    print("1. 远程服务器（自动开启数据库和日志，其余不开启）  2. 本地")
    selected = prompt_choice("请输入选项", {"1": ENV_TYPE_REMOTE, "2": ENV_TYPE_LOCAL}, "1")
    return str(selected)
```

### 5. 新增 `prompt_should_modify_existing()` 并在 `main()` 中调用

检测逻辑放在 `main()` 最前面，不进入 `collect_answers()`：

```python
def prompt_should_modify_existing(env_path: Path, yaml_path: Path) -> bool:
    if not env_path.exists() and not yaml_path.exists():
        return True  # 没有配置，直接进入初始化
    print("检测到已有配置文件。")
    selected = prompt_choice(
        "是否要修改现有配置？1. 不修改（默认）  2. 修改\n请输入选项",
        {"1": False, "2": True},
        "1",
    )
    return bool(selected)
```

`main()` 中：

```python
def main() -> None:
    project_root = PROJECT_ROOT
    env_path = env_file_path(project_root)
    yaml_path = project_root / "config.yaml"

    if not prompt_should_modify_existing(env_path, yaml_path):
        print("已跳过配置修改。")
        print("运行 `uv run work-mcp` 启动服务。")
        return

    try:
        answers = collect_answers(project_root)
    ...
```

### 6. `collect_answers()` 重构后结构

```python
def collect_answers(project_root: Path = PROJECT_ROOT) -> SetupAnswers:
    env_values = parse_env_file(env_file_path(project_root))
    yaml_values = load_existing_yaml(project_root / "config.yaml")
    existing_plugins = enabled_plugins_from_yaml(yaml_values)

    print("开始初始化配置。")

    # --- 阶段一：确定各插件开关 ---
    env_type = prompt_environment_type()

    if env_type == ENV_TYPE_REMOTE:
        print("远程服务器模式：已默认开启数据库和日志搜索，其余插件不开启。")
        enable_database = True
        enable_log_search = True
        enable_dingtalk = False
        enable_jira = False
    else:
        print("请选择要开启的模块；直接回车表示不开启。")
        enable_database = resolve_plugin_enabled("database", current_enabled=PLUGIN_DATABASE in existing_plugins)
        enable_log_search = resolve_plugin_enabled("log_search", current_enabled=PLUGIN_LOG_SEARCH in existing_plugins)
        enable_dingtalk = resolve_plugin_enabled("dingtalk", current_enabled=PLUGIN_DINGTALK in existing_plugins)
        enable_jira = resolve_plugin_enabled("jira", current_enabled=PLUGIN_JIRA in existing_plugins)

    # --- 阶段二：按需收集各插件配置 ---
    database_answers: dict[str, object] = _default_database_answers()
    if enable_database:
        database_answers.update(collect_database_answers(env_values))
        database_answers.update(collect_sqlserver_answers(env_values, str(database_answers["db_type"])))

    log_search_answers: dict[str, str] = {"log_base_dir": ""}
    if enable_log_search:
        log_search_answers.update(collect_log_search_answers(yaml_values))

    dingtalk_answers: dict[str, str] = {"dingtalk_webhook_url": "", "dingtalk_secret": ""}
    if enable_dingtalk:
        dingtalk_answers.update(collect_dingtalk_answers(env_values))

    jira_answers: dict[str, str] = {"jira_base_url": "", "jira_api_token": "", "jira_project_key": ""}
    if enable_jira:
        jira_answers.update(collect_jira_answers(env_values))

    # --- 阶段三：组装结果 ---
    return SetupAnswers(
        enable_database=enable_database,
        ...
    )
```

`_default_database_answers()` 是一个小提取，把那坨默认 dict 收拢进去，让阶段二的初始化统一风格。

---

## 改动文件

只涉及 `scripts/init_config.py`，`src/work_mcp/setup.py` 不需要动。

## 改动顺序

1. 提取 `collect_log_search_answers()` 和 `collect_dingtalk_answers()`，验证逻辑等价
2. 提取 `_default_database_answers()`，统一各插件默认值风格
3. 删除 `prompt_sqlserver_trust_cert()`，SSL 固定 `False`
4. 新增 `prompt_environment_type()`，在 `collect_answers()` 中接入分支
5. 新增 `prompt_should_modify_existing()`，在 `main()` 中接入早退
