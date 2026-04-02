## work-assistant-mcp

An MCP server for work-related tools used by local agents.

Current tools:

- `dingtalk_send_markdown`

## What This Server Is For

Use this server when a local agent needs to send work updates into a DingTalk group, for example:

- task progress updates
- completion notifications
- error reports
- manual smoke-test messages

## Configuration

Configuration is split into two files by sensitivity:

### `config.yaml` — non-sensitive settings

Controls which tools are enabled and sets logging and server options. Committed to the repository.

```yaml
server:
  name: work-assistant-mcp
  instructions: "A work-focused MCP server with notification tools for local agents."

logging:
  dir: logs
  level: info   # debug | info | warning | error

tools:
  enabled:
    - dingtalk
    # comment out any line to disable that tool at startup
```

To disable a tool without removing it from the codebase, comment out its name in `tools.enabled`.

### `.env` — sensitive credentials

Copy `.env.example` to `.env` and fill in the DingTalk robot settings:

```env
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=your_token_here
DINGTALK_SECRET=SECxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Notes:

- `DINGTALK_WEBHOOK_URL` is required.
- `DINGTALK_SECRET` is optional only if the robot does not have "加签" enabled.
- If "加签" is enabled in DingTalk, `DINGTALK_SECRET` must be set or sends will fail with a signature mismatch error.
- Keep real tokens and secrets only in local `.env` or environment variables. Do not commit them.

### Environment variable overrides

Environment variables take priority over `config.yaml`. This is useful for CI/CD or Docker deployments:

| Variable                   | Overrides       |
| -------------------------- | --------------- |
| `WORK_ASSISTANT_LOG_DIR`   | `logging.dir`   |
| `WORK_ASSISTANT_LOG_LEVEL` | `logging.level` |

## Adding a New Tool

1. Implement `register_<name>_tools(mcp: FastMCP)` in `src/work_assistant_mcp/tools/<name>.py`.
2. Add an entry to `TOOL_REGISTRY` in `src/work_assistant_mcp/tools/__init__.py`.
3. Add the tool name to `tools.enabled` in `config.yaml`.

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

Agent guidance:

- Use `dingtalk_send_markdown` when the user or team should be notified in DingTalk.
- Set `title` to a short subject line.
- Set `markdown` to the full message body.
- Do not send routine chatter unless the user asked for a notification or the workflow clearly requires one.

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
```

Run smoke tests:

```bash
uv run pytest
```
