from __future__ import annotations

from ...hints import STOP_AND_NOTIFY_USER_INSTRUCTION

TOOL_DB_LIST_DATABASES = "db_list_databases"
TOOL_DB_LIST_TABLES = "db_list_tables"
TOOL_DB_GET_TABLE_SCHEMA = "db_get_table_schema"
TOOL_DB_EXECUTE_QUERY = "db_execute_query"

QUERY_DEFAULT_LIMIT = 5
QUERY_MAX_LIMIT = 50

DB_LIST_DATABASES_DESCRIPTION = f"""\
List databases visible to the configured SQL Server account.

Use this first when you need to inspect live database data but do not yet know which
database contains the relevant tables.
"""

DB_LIST_TABLES_DESCRIPTION = f"""\
List tables in a specific database.

Use this after {TOOL_DB_LIST_DATABASES} to identify candidate tables before requesting
schema details or running a query.
"""

DB_GET_TABLE_SCHEMA_DESCRIPTION = f"""\
Return the column definitions for a database table.

Use this before writing a query so you can confirm the available columns, data types,
nullability, and primary-key fields.
"""

DB_EXECUTE_QUERY_DESCRIPTION = f"""\
Execute a read-only SELECT query against a database and return structured rows.

Use this to inspect live data during debugging after confirming the table schema with
{TOOL_DB_GET_TABLE_SCHEMA}. Only a single SELECT statement is accepted.
"""

HINT_DATABASE_NOT_FOUND = (
    f"The database was not found or is not accessible. Call {TOOL_DB_LIST_DATABASES} "
    "to get a valid database name, then retry."
)

HINT_TABLE_NOT_FOUND = (
    "The table '{table}' was not found in database '{database}'. "
    f"Call {TOOL_DB_LIST_TABLES} with that database to get valid table names, then retry."
)

HINT_QUERY_ERROR = (
    f"The query failed. Call {TOOL_DB_GET_TABLE_SCHEMA} to verify table and column names, "
    "then retry with a corrected SELECT statement."
)

HINT_NO_DATABASES = (
    "No databases were returned. The configured user account may lack visibility permissions. "
    f"{STOP_AND_NOTIFY_USER_INSTRUCTION}"
)
