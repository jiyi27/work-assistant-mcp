from __future__ import annotations

import asyncio
from pathlib import Path

from work_mcp.config import DatabaseSettings, ServerSettings, Settings
from work_mcp.server import create_mcp
from work_mcp.tools.database.base import (
    AbstractDatabaseClient,
    DatabaseConnectionError,
    DatabaseNotFoundError,
    QueryExecutionError,
    QueryResult,
    TableNotFoundError,
)
from work_mcp.tools.database.security import ReadOnlyViolation, validate_read_only_query
from work_mcp.tools.database.service import DatabaseService

_DEFAULT_SERVER = ServerSettings(transport="stdio", host=None, port=None)
_DEFAULT_DATABASE = DatabaseSettings(
    db_type="sqlserver",
    host="db.example.internal",
    port=1433,
    user="readonly_user",
    password="secret",
    default_database="master",
    driver="ODBC Driver 18 for SQL Server",
    trust_server_certificate=False,
    connect_timeout_seconds=5,
)


def _make_settings(**overrides: object) -> Settings:
    defaults = dict(
        server=_DEFAULT_SERVER,
        dingtalk_webhook_url="https://example.invalid/webhook",
        dingtalk_secret=None,
        jira_base_url="https://jira.example.invalid",
        jira_api_token="jira-token",
        jira_project_key="IOS",
        log_dir=Path("logs"),
        log_level="info",
        enabled_plugins=("database",),
        jira_latest_assigned_statuses=("待处理", "已接收", "处理中"),
        jira_start_target_status="已接收",
        jira_resolve_target_status="已解决",
        jira_attachment_max_images=5,
        jira_attachment_max_bytes=1_048_576,
        log_search=None,
        database=_DEFAULT_DATABASE,
    )
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


class FakeDatabaseClient(AbstractDatabaseClient):
    def __init__(self) -> None:
        self.listed_databases = ["app_db", "reporting_db"]

    def list_databases(self) -> list[str]:
        return self.listed_databases

    def list_tables(self, database: str) -> list[str]:
        if database == "missing_db":
            raise DatabaseNotFoundError("missing")
        return ["orders", "users"]

    def get_table_schema(self, database: str, table: str) -> list[dict[str, object]]:
        if database == "missing_db":
            raise DatabaseNotFoundError("missing")
        if table == "missing_table":
            raise TableNotFoundError("missing")
        return [
            {
                "column": "id",
                "type": "int",
                "nullable": False,
                "primary_key": True,
            }
        ]

    def execute_query(self, database: str, sql: str, limit: int) -> QueryResult:
        if database == "missing_db":
            raise DatabaseNotFoundError("missing")
        if "bad_column" in sql:
            raise QueryExecutionError("Invalid column name 'bad_column'.")
        if "boom" in sql:
            raise DatabaseConnectionError("connection lost")
        return QueryResult(
            columns=["id", "status"],
            rows=[[1, "pending"]],
            row_count=1,
            truncated=False,
        )


def test_validate_read_only_query_rejects_multiple_statements() -> None:
    try:
        validate_read_only_query("SELECT 1; SELECT 2")
    except ReadOnlyViolation as exc:
        assert "single statement" in str(exc)
    else:
        raise AssertionError("expected ReadOnlyViolation")


def test_validate_read_only_query_rejects_non_select_statement() -> None:
    try:
        validate_read_only_query("UPDATE users SET active = 1")
    except ReadOnlyViolation as exc:
        assert "Only SELECT statements" in str(exc)
    else:
        raise AssertionError("expected ReadOnlyViolation")


def test_validate_read_only_query_rejects_select_into() -> None:
    try:
        validate_read_only_query("SELECT * INTO backup_users FROM users")
    except ReadOnlyViolation as exc:
        assert "SELECT INTO" in str(exc)
    else:
        raise AssertionError("expected ReadOnlyViolation")


def test_database_service_returns_empty_database_hint() -> None:
    client = FakeDatabaseClient()
    client.listed_databases = []
    service = DatabaseService(_make_settings(), client=client)

    structured = service.list_databases()

    assert structured["success"] is True
    assert structured["databases"] == []
    assert "hint" in structured


def test_database_service_returns_structured_query_error() -> None:
    service = DatabaseService(_make_settings(), client=FakeDatabaseClient())

    structured = service.execute_query("app_db", "SELECT bad_column FROM users", 5)

    assert structured == {
        "success": False,
        "error_type": "query_error",
        "message": "Invalid column name 'bad_column'.",
        "hint": "The query failed. Call db_get_table_schema to verify table and column names, then retry with a corrected SELECT statement.",
    }


def test_database_service_returns_internal_error_for_connection_failure() -> None:
    service = DatabaseService(_make_settings(), client=FakeDatabaseClient())

    structured = service.execute_query("app_db", "SELECT boom FROM users", 5)

    assert structured == {
        "success": False,
        "error_type": "internal_error",
        "message": "connection lost",
        "hint": "An internal error occurred. Retry up to 2 times; if still failing, stop and notify the user with the message above.",
    }


def test_database_service_returns_successful_query_result() -> None:
    service = DatabaseService(_make_settings(), client=FakeDatabaseClient())

    structured = service.execute_query("app_db", "SELECT id, status FROM users", 5)

    assert structured == {
        "success": True,
        "database": "app_db",
        "columns": ["id", "status"],
        "rows": [[1, "pending"]],
        "row_count": 1,
        "truncated": False,
    }


def test_database_tools_are_registered_when_database_plugin_enabled() -> None:
    mcp = create_mcp(_make_settings())

    tools = asyncio.run(mcp.list_tools())

    assert [tool.name for tool in tools] == [
        "db_list_databases",
        "db_list_tables",
        "db_get_table_schema",
        "db_execute_query",
    ]
