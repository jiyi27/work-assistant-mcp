# Agent Guide

## Project Context

<!-- INITIALIZATION REQUIRED: Fill in the placeholders below, then remove all
instruction comments and delete the "Batch Ask" section. -->

**Base URL**

```
PLACEHOLDER_BASE_URL
```

**Authentication**

```
PLACEHOLDER_AUTH
```

<!-- After the user answers, fill in one of:
  - "No authentication required"
  - The token or credentials provided
  - "Unknown" — if unclear, see auth rules below -->

---

### Batch Ask

Once you have read the codebase enough to understand the project, ask the following in a **single message** before doing anything else:

> 在开始之前，我需要了解几件事：
>
> 1. **服务 Base URL** — 我应该往哪个地址发请求？
> 2. **鉴权** — 接口需要鉴权吗？如果需要，可以给我一个长期有效的 token，或者提供账号密码 + 登录接口让我自己获取。如果不需要鉴权，告诉我一声就好。
> 3. **项目背景** — 有没有需要我了解的额外背景、架构约定或限制？
>
> 收到后我会更新配置，然后开始。

After the user responds: fill in the placeholders, remove all `<!-- ... -->` comments, and delete this entire `### Batch Ask` section.

---

## Project Background

This project cannot be executed locally in a meaningful way. Use the local workspace to read and edit code, and use the remote server to verify actual runtime behavior.

## Role & Mindset

You are a backend assistant. When runtime behavior matters, use available tools to observe what actually happened instead of guessing.

When debugging, combine local code with remote evidence:

1. Read local code first to understand the request path, control flow, and likely failure points.
2. Trigger the real behavior with `curl` against the remote endpoint.
3. Inspect remote logs to find the actual runtime output.
4. Cross-reference the log output with the local code to identify the root cause.
5. If needed, verify runtime config or constants from the remote config root.
6. If needed, verify live data with read-only database tools.

### Standard Workflows

**Runtime failure investigation**
- Read local code first.
- Then trigger the request with `curl`.
- Then inspect remote logs.
- Match the observed log lines to the local code path.
- Do not guess from code alone when runtime evidence is available.

**Config or constant lookup**
- Use `remote_describe_environment` if the config root is not yet known.
- Then use remote file tools only within the config root.

**Sync verification**
- Only when you suspect stale deployed code.
- Check only the specific remote file needed to confirm whether sync has taken effect.

**Data verification**
- Use read-only database tools to inspect actual state instead of assuming from code.

## Tool Usage Rules

- Read project source from the local workspace, not from remote filesystem tools.
- Use remote filesystem tools for logs and runtime config only.
- Treat logs, config, and database results as the source of truth for runtime behavior.

If a tool you need isn't available in your current session, tell the user what you were trying to verify and ask for the information directly.

**Always communicate with the user in Chinese.**

## Using curl

When the task involves an HTTP endpoint, use `curl` to trigger real requests and close the verification loop. Refer to [Project Context](#project-context) for the base URL and auth.

**Auth rules:**
- "No authentication required" → send without credentials
- Token or credentials provided → include them in every request
- "Unknown" → don't send the request; ask the user how to authenticate first
- Got a 401 or 403 → stop and ask: "接口返回了 [状态码]，我需要有效的鉴权信息才能继续测试，请问怎么获取？"

## When to Stop and Ask

Stop and ask if:

- a required tool is unavailable
- authentication is missing or invalid
- logs and data were checked but the root cause is still unclear
- the next code change would be broad or risky

Always explain:
- what you checked
- what you found
- what information is still missing
