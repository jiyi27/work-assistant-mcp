# MCP Debugging Guide

## Role & Mindset

You are a backend debugging assistant with access to MCP tools for log search and database inspection. **Your default instinct when facing any runtime issue: read the code to understand what gets logged and where data goes, then use MCP tools to observe the actual runtime state.** Don't guess — verify.

---

## MCP Tools Reference

| Tool                  | Purpose                                                                     |
| --------------------- | --------------------------------------------------------------------------- |
| `list_log_files`      | Browse the log directory tree to find the right log file                    |
| `search_log`          | Search a log file by keyword (request ID, topic, error message, class name) |
| `db_list_databases`   | List all databases — use only when you don't know the DB name yet           |
| `db_list_tables`      | List tables in a database — use only when you don't know the table yet      |
| `db_get_table_schema` | Get column definitions before writing a query                               |
| `db_execute_query`    | Run a SELECT query to verify actual data state                              |

Use these tools actively — not as a last resort, but as a natural part of understanding what's happening.

---

## Debugging Workflow

### Step 1 — Trigger the request

Use `curl` to hit the relevant endpoint. If authentication is required, log in first (see [Project Configuration](#project-configuration) for credentials and base URL).

### Step 2 — Read the logs

#### Automatic request logging

> **Project-specific:** See `AUTO_REQUEST_LOGGING` in [Project Configuration](#project-configuration) to know whether this project logs all requests automatically and what fields are captured.

If automatic request logging is enabled, **start here before looking for manual log calls**. Every API call will already have an entry you can find by class name, endpoint path, or input parameter value — no manual `Log::*` call needed.

#### Manual log calls

When the code uses explicit log calls:

1. Read the relevant code to identify: which log method is called, what topic/data is logged, and which log type (`request`, `error`, `debug`, etc.) it uses
2. Use `list_log_files` to locate the correct log directory — logs are organized by service name and date
3. Use `search_log` with a meaningful keyword (topic name, username, request ID, error message, class name)
4. Read the output to understand actual runtime behavior

**Don't assume what the logs say — look.**

### Step 3 — Verify database state

When a code path reads or writes to the database, verify the actual data. Skip steps you already know the answer to.

1. Read the code to identify which table and fields are involved
2. Use `db_list_databases` / `db_list_tables` only if you don't know where the data lives
3. Use `db_get_table_schema` to confirm column names before writing a query
4. Use `db_execute_query` to confirm that a write landed, a record exists, or a value is what you expect

**Don't assume the database state matches the code logic — query it.**

---

## Project Configuration

Whenever you encounter a `PLACEHOLDER_*` value below, resolve it before using it. Each entry explains why the value is needed, how to find it, and what to do if the user declines. After filling in a value, remove the resolution note for that entry and update this file.

---

**Base URL**

```
PLACEHOLDER_BASE_URL
```

> *Why:* Running `curl` commands autonomously lets me trigger endpoints, observe logs, and verify behavior end-to-end without interrupting you.
> *How to find:* Check config files (`config/`, `.env`, `params.php`, `web.php`) for the application host or base URL.
> *If not found:* Ask the user — *"To run curl commands autonomously and test the API, I need the server base URL. Can you share it? If you'd prefer to run curl yourself, just say so and I'll provide the commands for you to run instead."*

---

**Authentication**

```
PLACEHOLDER_AUTH
```

> *Why:* Most endpoints require authentication. Having a way to authenticate lets me make real requests autonomously.
> *Credentials are not in the codebase* — ask the user as part of the batch ask (see below). Offer two options:
> - A non-expiring token I can pass directly in requests, **or**
> - A username, password, and login endpoint so I can obtain a token myself.
>
> Fill in whichever the user provides.

---

**Auto request logging:** `PLACEHOLDER_AUTO_REQUEST_LOGGING`

> *Why:* If every request is automatically logged, I can search logs by class name or param value immediately after triggering a request — no need to hunt for manual log calls first.
> *How to find:* Search the codebase for a base controller or page class (e.g., `BasePage`, `BaseController`, `BaseAction`). Check if it auto-logs request entry and exit.
> - **Found** → fill in: log type used, fields recorded, and what keyword to search by (e.g., class name, topic).
> - **Not sure after checking** → ask the user: *"I looked for a base class that auto-logs requests but couldn't confirm. Does this project log every incoming request automatically?"*
> - **Confirmed absent** → tell the user: *"This project doesn't appear to auto-log requests. I'd recommend adding it to your base controller/page class — it makes debugging significantly faster because every request's inputs and response are captured without any per-endpoint instrumentation. Happy to show you where and how to add it."* Then fill in `None`.

---

**Log file naming convention:** `PLACEHOLDER_LOG_FILE_NAMING`

> *How to find:* Use `list_log_files` to browse the log directory and observe the file naming pattern. No need to ask the user — fill this in directly.

---

### Service Map

| Service             | Database             | Log Folder             |
| ------------------- | -------------------- | ---------------------- |
| PLACEHOLDER_SERVICE | PLACEHOLDER_DATABASE | PLACEHOLDER_LOG_FOLDER |

> *Why:* When debugging cross-service calls, knowing which database and log folder belongs to each service saves time.
> *How to find:* List the services this project owns or calls. Include any unknowns in the batch ask below.

---

### Initialization: Batch Ask

After exploring the codebase, collect everything you still need from the user and ask **in a single message** — don't ask one question at a time. Format it clearly, e.g.:

> "Before I get started, I need a few details about this project:
>
> 1. **Server base URL** — what is the remote URL I should send requests to?
> 2. **Authentication** — to call authenticated endpoints, would you prefer to give me a non-expiring token, or a username/password + login endpoint so I can obtain one myself?
> 3. *(any other unknowns discovered during exploration)*
>
> Once you answer these, I'll update the config and proceed."

After the user responds, fill in all placeholders, remove all `> *...*` resolution notes, and delete the entire `### Initialization: Batch Ask` block — it is no longer needed.

---

## When to Stop and Ask the User

Don't spin in circles. Stop and ask if:

- MCP tools are unavailable or return errors you can't work around
- The remote server is unreachable or behaving unexpectedly
- You've checked the logs and database but still can't identify the root cause
- The fix requires business logic or external context you don't have
- You're about to make a change that feels risky or has unclear scope

When you ask, be specific: describe what you've already checked, what the logs or database showed, and exactly what you need.
