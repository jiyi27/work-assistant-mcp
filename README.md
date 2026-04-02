## work-assistant-mcp

An MCP server for work-related tools used by local agents.

Current tool:

- `dingtalk_send_markdown`

## Configuration

Copy `.env.example` to `.env` and fill in your DingTalk robot webhook.

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
