from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP

from ...config import Settings
from .service import DatabaseService
from .strings import (
    DB_GET_TABLE_SCHEMA_DESCRIPTION,
    DB_LIST_DATABASES_DESCRIPTION,
    DB_LIST_TABLES_DESCRIPTION,
    TOOL_DB_EXECUTE_QUERY,
    TOOL_DB_GET_TABLE_SCHEMA,
    TOOL_DB_LIST_DATABASES,
    TOOL_DB_LIST_TABLES,
    db_execute_query_description,
)


def register_database_tools(mcp: FastMCP, settings: Settings) -> None:
    service = DatabaseService(settings)

    @mcp.tool(name=TOOL_DB_LIST_DATABASES, description=DB_LIST_DATABASES_DESCRIPTION)
    def db_list_databases() -> dict[str, Any]:
        return service.list_databases()

    @mcp.tool(name=TOOL_DB_LIST_TABLES, description=DB_LIST_TABLES_DESCRIPTION)
    def db_list_tables(
        database: Annotated[
            str,
            f"Exact runtime database name returned by {TOOL_DB_LIST_DATABASES}, or confirmed from code/config. Do not guess logical aliases.",
        ],
    ) -> dict[str, Any]:
        return service.list_tables(database)

    @mcp.tool(
        name=TOOL_DB_GET_TABLE_SCHEMA,
        description=DB_GET_TABLE_SCHEMA_DESCRIPTION,
    )
    def db_get_table_schema(
        database: Annotated[
            str,
            f"Exact runtime database name returned by {TOOL_DB_LIST_DATABASES}, or confirmed from code/config. Do not guess logical aliases.",
        ],
        table: Annotated[
            str,
            f"Exact runtime table name returned by {TOOL_DB_LIST_TABLES}, or confirmed from ORM metadata such as db_table / __tablename__. Do not guess from model class names.",
        ],
    ) -> dict[str, Any]:
        return service.get_table_schema(database, table)

    @mcp.tool(
        name=TOOL_DB_EXECUTE_QUERY,
        description=db_execute_query_description(settings.database.db_type),
    )
    def db_execute_query(
        database: Annotated[
            str,
            f"Exact runtime database name returned by {TOOL_DB_LIST_DATABASES}, or confirmed from code/config. Do not guess logical aliases.",
        ],
        sql: Annotated[str, "A single SELECT statement used to inspect live data."],
    ) -> dict[str, Any]:
        return service.execute_query(database, sql)
