# 配置与部署

这份文档只保留运行方式和最小配置建议。字段级说明、完整示例和工具清单以 [README.md](../README.md) 为准。

## 配置原则

所有运行时配置都放在 `config.yaml`。

启动时只会读取并校验 `plugins.enabled` 里列出的插件配置。未启用插件的配置段即使保留在 `config.yaml` 中，也不会阻塞启动。

如果需要在启动前检查配置和连通性，执行：

```bash
make check
```

它只检查当前启用的插件。

## 推荐运行方式

推荐按部署位置区分两种模式。

- 本地模式：通常启用 `jira`，通过 `stdio` 由 MCP 客户端直接拉起本地进程。
- 远程模式：通常启用 `database`、`remote_fs`，通过 HTTP 暴露 `/mcp` 端点。

这只是推荐，不是强约束。实际启用哪些插件，以 `config.yaml` 中的 `plugins.enabled` 为准。

## 本地模式

最小示例：

```yaml
plugins:
  enabled:
    - jira

jira:
  base_url: https://your-jira-instance.example.com
  api_token: your_jira_api_token_here
  project_key: PROJECT1
  latest_assigned_statuses:
    - 待处理
    - 已接收
  start_target_status: 已接收
  resolve_target_status: 已解决
```

客户端通常直接拉起：

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

也可以直接运行：

```bash
uv run work-mcp
```

## 远程模式

最小示例：

```yaml
plugins:
  enabled:
    - database
    - remote_fs

database:
  type: mysql
  host: your-db-host.example.com
  user: readonly_user
  password: your_password_here

log_search:
  log_base_dir: /absolute/path/to/logs
```

HTTP 方式启动：

```bash
make run
```

默认监听 `0.0.0.0:8182`，MCP 端点为：

```text
http://<server-host>:8182/mcp
```

如需覆盖地址或端口：

```bash
make run HOST=127.0.0.1 PORT=9000
```

## 手动初始化

如果还没有配置文件，可以直接复制模板：

```bash
cp config.example.yaml config.yaml
```

然后按实际需要删掉未启用插件，或只保留你准备启用的插件配置。

## 说明

- 当前不再推荐使用配置引导脚本作为主流程。
- 如果你只是想知道某个字段怎么填，看 [README.md](../README.md)。
- 如果你需要 SQL Server，先在运行机器上安装 ODBC Driver 18 for SQL Server。
