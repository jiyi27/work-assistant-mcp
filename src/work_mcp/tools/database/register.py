from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP

from ...config import Settings
from .service import DatabaseService
from .strings import (
    DB_EXECUTE_QUERY_DESCRIPTION,
    DB_GET_TABLE_SCHEMA_DESCRIPTION,
    DB_LIST_DATABASES_DESCRIPTION,
    DB_LIST_TABLES_DESCRIPTION,
    QUERY_DEFAULT_LIMIT,
    TOOL_DB_EXECUTE_QUERY,
    TOOL_DB_GET_TABLE_SCHEMA,
    TOOL_DB_LIST_DATABASES,
    TOOL_DB_LIST_TABLES,
)


def register_database_tools(mcp: FastMCP, settings: Settings) -> None:
    service = DatabaseService(settings)

    @mcp.tool(name=TOOL_DB_LIST_DATABASES, description=DB_LIST_DATABASES_DESCRIPTION)
    def db_list_databases() -> dict[str, Any]:
        return service.list_databases()

    @mcp.tool(name=TOOL_DB_LIST_TABLES, description=DB_LIST_TABLES_DESCRIPTION)
    def db_list_tables(
        database: Annotated[str, f"Database name returned by {TOOL_DB_LIST_DATABASES}."],
    ) -> dict[str, Any]:
        return service.list_tables(database)

    @mcp.tool(
        name=TOOL_DB_GET_TABLE_SCHEMA,
        description=DB_GET_TABLE_SCHEMA_DESCRIPTION,
    )
    def db_get_table_schema(
        database: Annotated[str, f"Database name returned by {TOOL_DB_LIST_DATABASES}."],
        table: Annotated[str, f"Table name returned by {TOOL_DB_LIST_TABLES}."],
    ) -> dict[str, Any]:
        return service.get_table_schema(database, table)

    @mcp.tool(name=TOOL_DB_EXECUTE_QUERY, description=DB_EXECUTE_QUERY_DESCRIPTION)
    def db_execute_query(
        database: Annotated[str, f"Database name returned by {TOOL_DB_LIST_DATABASES}."],
        sql: Annotated[str, "A single SELECT statement used to inspect live data."],
        limit: Annotated[int, "Maximum rows to return. Must be between 1 and 50."] = QUERY_DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        return service.execute_query(database, sql, limit)
