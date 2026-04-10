# 配置与启动

本文档引导你从零完成 work-mcp 的环境搭建、配置和启动。

---

## 1. 安装

**前置条件：** [uv](https://docs.astral.sh/uv/)

```bash
git clone <你的仓库地址> work-mcp
cd work-mcp
uv sync
```

### SQL Server 额外依赖 (MySQL 用户跳过此步)

使用 `database` 插件且数据库类型为 SQL Server 时，需要在主机上安装 Microsoft ODBC Driver：

```bash
# macOS
brew install microsoft/mssql-release/msodbcsql18

# Ubuntu（18.04 / 20.04 / 22.04 / 24.04）
curl -sSL -O https://packages.microsoft.com/config/ubuntu/$(grep VERSION_ID /etc/os-release | cut -d '"' -f 2)/packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb && rm packages-microsoft-prod.deb
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18

# Debian（9 / 10 / 11 / 12 / 13）
curl -sSL -O https://packages.microsoft.com/config/debian/$(grep VERSION_ID /etc/os-release | cut -d '"' -f 2 | cut -d '.' -f 1)/packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb && rm packages-microsoft-prod.deb
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18

# RHEL / Oracle Linux（7 / 8 / 9 / 10）
curl -sSL -O https://packages.microsoft.com/config/rhel/$(grep VERSION_ID /etc/os-release | cut -d '"' -f 2 | cut -d '.' -f 1)/packages-microsoft-prod.rpm
sudo yum install packages-microsoft-prod.rpm && rm packages-microsoft-prod.rpm
sudo ACCEPT_EULA=Y yum install -y msodbcsql18
```

---

## 2. 交互式配置（推荐）

运行向导，自动生成 `.env` 和 `config.yaml`：

```bash
make init
```

向导会依次询问是否启用各插件，并收集对应凭据：

- `database` → 数据库类型、主机、端口、用户名、密码
- `log_search` → 日志根目录（绝对路径）
- `dingtalk` → Webhook URL 和签名密钥（可选）
- `jira` → Jira 实例地址、API Token、项目 key

完成后生成两个文件：

| 文件 | 内容 |
|------|------|
| `.env` | 数据库密码、Token 等敏感凭据 |
| `config.yaml` | 插件开关、日志级别等非敏感配置 |

---

## 3. 校准 Jira 工作流状态（启用 Jira 时）

`make init` 会在 `config.yaml` 中写入默认的状态名称占位值，这些名称需要替换为你的 Jira 项目实际使用的状态名称。

**查询当前项目的状态名称：**

```bash
uv run python scripts/inspect_jira_issue_workflow.py <ISSUE-KEY>
```

用输出结果修改 `config.yaml` 中的对应值：

```yaml
jira:
  latest_assigned_statuses:
    - 待处理      # jira_get_latest_assigned_issue 返回这些状态的 issue
    - 处理中
  start_target_status: 处理中   # jira_start_issue 流转目标状态
  resolve_target_status: 已解决 # jira_resolve_issue 流转目标状态
```

状态名称必须与 Jira 工作流完全一致。字段详细说明见 [`config.example.yaml`](../config.example.yaml)。

---

## 4. 验证配置

```bash
make doctor
```

输出每项检查的结果（`[ok]` / `[warn]` / `[error]`）。存在 `[error]` 时服务无法正常启动，根据提示修正后重新运行。

---

## 5. 连接到 Agent

在 MCP 客户端（如 Claude Desktop、Cursor）的配置中添加：

```json
{
  "mcpServers": {
    "work-mcp": {
      "command": "uv",
      "args": ["run", "work-mcp"],
      "cwd": "/absolute/path/to/work-mcp"
    }
  }
}
```

这会以 `stdio` 模式启动服务，是本地 Agent 集成的默认方式。

---

## 6. 直接运行（调试用）

```bash
# stdio 模式（供 MCP 客户端直接调用）
uv run work-mcp

# HTTP 模式（供调试或远程访问）
make run                        # 默认监听 0.0.0.0:8182
make run HOST=127.0.0.1 PORT=9000
```

HTTP 模式启动后，MCP 端点地址为 `http://<host>:<port>/mcp`。

---

## 附录：手动配置文件

不想使用 `make init` 时，可以手动创建配置文件：

```bash
cp .env.example .env
cp config.example.yaml config.yaml
```

然后编辑两个文件，按需填写。所有字段的说明见 [`config.example.yaml`](../config.example.yaml)。
