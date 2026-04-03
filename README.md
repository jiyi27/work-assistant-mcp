## work-assistant-mcp

An MCP server for work-related tools used by local agents.

Tools are grouped by integration. Each integration is enabled or disabled as a unit in `config.yaml`.

| Integration | Tools                                                               |
| ----------- | ------------------------------------------------------------------- |
| `dingtalk`  | `dingtalk_send_markdown`                                            |
| `jira`      | `jira_get_latest_assigned_issue`, `jira_get_attachment_image`, `jira_start_issue`, `jira_resolve_issue` |

## Configuration

Configuration is split into two files by sensitivity:

### `config.yaml` — non-sensitive settings

Controls which integrations are enabled and sets logging, server options, and Jira policy. Committed to the repository.

```yaml
server:
  name: work-assistant-mcp
  instructions: "A work-focused MCP server with notification tools for local agents."

logging:
  dir: logs
  level: info   # debug | info | warning | error

integrations:
  enabled:
    - dingtalk
    # - jira
    # comment out any line to disable that integration at startup

jira:
  latest_assigned_statuses:
    - 待处理
    - 已接收
    - 处理中
  start_target_status: 已接收
  resolve_target_status: 已解决
  attachments:
    max_images: 5
    max_bytes_per_image: 1048576
```

To disable an integration (and all its tools) without removing it from the codebase, comment out its name in `integrations.enabled`.
When `jira` is enabled, `jira.latest_assigned_statuses`, `jira.start_target_status`, and `jira.resolve_target_status` must be configured explicitly.
These values are Jira status names, not Jira status categories.

### `.env` — sensitive credentials

Copy `.env.example` to `.env` and fill in the required credentials:

```env
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=your_token_here
DINGTALK_SECRET=SECxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
JIRA_BASE_URL=https://your-jira-instance.example.com
JIRA_API_TOKEN=your_jira_api_token_here
JIRA_PROJECT_KEY=PROJECT1
```

Notes:

- `DINGTALK_WEBHOOK_URL` is required.
- `DINGTALK_SECRET` is optional only if the robot does not have "加签" enabled.
- If "加签" is enabled in DingTalk, `DINGTALK_SECRET` must be set or sends will fail with a signature mismatch error.
- `JIRA_BASE_URL`, `JIRA_API_TOKEN`, and `JIRA_PROJECT_KEY` are required only when the `jira` integration is enabled.
- Jira authentication is fixed to `Authorization: Bearer <JIRA_API_TOKEN>` to match the working deployment behavior.
- `JIRA_PROJECT_KEY` defines the single Jira project this server is allowed to query and update.
- Keep real tokens and secrets only in local `.env` or environment variables. Do not commit them.

### Environment variable overrides

Environment variables take priority over `config.yaml`. This is useful for CI/CD or Docker deployments:

| Variable                   | Overrides       |
| -------------------------- | --------------- |
| `WORK_ASSISTANT_LOG_DIR`   | `logging.dir`   |
| `WORK_ASSISTANT_LOG_LEVEL` | `logging.level` |

## Adding a New Tool

1. Implement `register_<name>_tools(mcp: FastMCP, settings: Settings)` under `src/work_assistant_mcp/tools/`.
2. Keep simple integrations in a single module such as `src/work_assistant_mcp/tools/<name>.py`.
3. When an integration grows into multiple focused files, group it as a package such as `src/work_assistant_mcp/tools/<name>/`.
4. Add an entry to `INTEGRATION_REGISTRY` in `src/work_assistant_mcp/tools/__init__.py`.
5. Add the integration name to `integrations.enabled` in `config.yaml`.

## Agent Setup

Point your MCP client or agent at the packaged entry point:

```json
{
  "mcpServers": {
    "work-assistant": {
      "command": "uv",
      "args": ["run", "work-assistant-mcp"],
      "cwd": "/absolute/path/to/work-assistant-mcp"
    }
  }
}
```

If your MCP client starts servers from the current repository root, `cwd` can usually be omitted.

## Run

```bash
uv run work-assistant-mcp
```

## Validate Locally

Use `scripts/preview_tool.py` to preview and debug tools registered by this server.

List tools:

```bash
uv run python scripts/preview_tool.py list
```

Show one tool's schema:

```bash
uv run python scripts/preview_tool.py describe dingtalk_send_markdown
```

Call one tool:

```bash
uv run python scripts/preview_tool.py call dingtalk_send_markdown \
  --args '{"title":"Smoke Test","markdown":"hello from local preview"}'
  

uv run python scripts/preview_tool.py call jira_get_attachment_image \
  --args '{"issue_key":"PAKISTAN-174","attachment_id":"24132"}'
```

Run smoke tests:

```bash
uv run pytest
```

Inspect one Jira issue's current status and available workflow transitions:

```bash
uv run python scripts/inspect_jira_issue_workflow.py IOS-123
```

This single command prints:

- all visible Jira `statusCategory` values
- all visible Jira `status` values
- the issue's current status
- every transition currently available for that issue

## Jira Configuration Workflow

Use this flow when configuring Jira tools for a new project or workflow:

1. Inspect one representative issue:

```bash
uv run python scripts/inspect_jira_issue_workflow.py IOS-123
```

2. Read the output fields:
- `statuses`: all visible Jira status names and their `statusCategory`
- `available_target_statuses`: statuses the current issue can move to right now
- `available_transitions`: transition names plus each transition's target status

3. Fill `config.yaml`:

```yaml
jira:
  latest_assigned_statuses:
    - 待处理
    - 已接收
    - 处理中
  start_target_status: 已接收
  resolve_target_status: 已解决
```

Guidance:

- `jira.latest_assigned_statuses` controls which issues `jira_get_latest_assigned_issue` is allowed to return.
- Put only concrete status names in `jira.latest_assigned_statuses`, such as `待处理` or `处理中`.
- Do not put status categories such as `Done` or `In Progress` into `jira.latest_assigned_statuses`.
- Set `jira.start_target_status` to one target status name that appears in `available_target_statuses` for issues you want to start.
- Set `jira.resolve_target_status` to one target status name that appears in `available_target_statuses` for issues you want to resolve.
- If Jira reports multiple transitions reaching the same target status, the tool stops with a structured `transition_ambiguous` error so you can adjust the workflow or rename statuses.

Behavior summary:

- `jira_get_latest_assigned_issue` queries only the configured project, only issues assigned to the current Jira user, and only issues whose current status is listed in `jira.latest_assigned_statuses`.
- `jira_start_issue` and `jira_resolve_issue` do not match `statusCategory`; they match the transition destination status name exactly.
