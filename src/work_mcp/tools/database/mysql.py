from __future__ import annotations

import atexit
from collections.abc import Sequence
from contextlib import closing
from threading import RLock
from typing import Any, Callable, NoReturn, Protocol, TypeVar, cast

from ...config import DatabaseSettings
from .base import (
    AbstractDatabaseClient,
    DatabaseConnectionError,
    DatabaseNotFoundError,
    QueryExecutionError,
    QueryResult,
    TableNotFoundError,
)

try:
    import pymysql
except ImportError:  # pragma: no cover - exercised via runtime error path
    pymysql = None

LIST_DATABASES_SQL = """
SELECT SCHEMA_NAME
FROM INFORMATION_SCHEMA.SCHEMATA
ORDER BY SCHEMA_NAME
"""

CONNECTIVITY_SQL = """
SELECT
    @@hostname AS server_name,
    DATABASE() AS database_name,
    CURRENT_USER() AS login_name
"""

LIST_TABLES_SQL = """
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = %s
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME
"""

TABLE_SCHEMA_SQL = """
SELECT
    c.COLUMN_NAME,
    c.COLUMN_TYPE,
    CASE WHEN c.IS_NULLABLE = 'YES' THEN 1 ELSE 0 END AS is_nullable,
    CASE WHEN k.COLUMN_NAME IS NULL THEN 0 ELSE 1 END AS is_primary_key
FROM INFORMATION_SCHEMA.COLUMNS AS c
LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS k
    ON k.TABLE_SCHEMA = c.TABLE_SCHEMA
    AND k.TABLE_NAME = c.TABLE_NAME
    AND k.COLUMN_NAME = c.COLUMN_NAME
    AND k.CONSTRAINT_NAME = 'PRIMARY'
WHERE c.TABLE_SCHEMA = %s
  AND c.TABLE_NAME = %s
ORDER BY c.ORDINAL_POSITION
"""

DATABASE_NOT_FOUND_CODES = {1044, 1049}
TABLE_NOT_FOUND_CODES = {1146}
QUERY_ERROR_CODES = {1054, 1064, 1149, 1222, 1241}
CONNECTION_ERROR_CODES = {
    0,
    1040,
    1042,
    1043,
    1045,
    2002,
    2003,
    2005,
    2013,
    2055,
}

T = TypeVar("T")
_MySqlRow = Sequence[object]
_MySqlDescription = Sequence[Sequence[object]]


def _ensure_pymysql_available() -> None:
    if pymysql is None:
        raise DatabaseConnectionError(
            "MySQL driver is not installed. Add the 'pymysql' package to the environment."
        )


def _mysql_error_type() -> type[Exception]:
    if pymysql is None:
        return Exception
    return cast(type[Exception], pymysql.MySQLError)


def _coerce_mysql_connection(raw_connection: object) -> _MySqlConnection:
    return cast(_MySqlConnection, raw_connection)


class _MySqlCursor(Protocol):
    description: _MySqlDescription | None

    def execute(self, sql: str, params: object = None) -> object: ...

    def fetchall(self) -> list[_MySqlRow]: ...

    def fetchone(self) -> _MySqlRow | None: ...

    def fetchmany(self, size: int) -> list[_MySqlRow]: ...

    def close(self) -> None: ...


class _MySqlConnection(Protocol):
    def cursor(self) -> _MySqlCursor: ...

    def close(self) -> None: ...


class MySqlClient(AbstractDatabaseClient):
    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings
        self._connections: dict[str, _MySqlConnection] = {}
        self._connections_lock = RLock()
        self._operation_locks: dict[str, RLock] = {}
        atexit.register(self.close)

    def list_databases(self) -> list[str]:
        def operation(cursor: _MySqlCursor) -> list[str]:
            cursor.execute(LIST_DATABASES_SQL)
            return [str(row[0]) for row in cursor.fetchall()]

        return self._run_with_cursor(None, operation)

    def list_tables(self, database: str) -> list[str]:
        def operation(cursor: _MySqlCursor) -> list[str]:
            cursor.execute(LIST_TABLES_SQL, (database,))
            return [str(row[0]) for row in cursor.fetchall()]

        return self._run_with_cursor(database, operation)

    def get_table_schema(self, database: str, table: str) -> list[dict[str, Any]]:
        def operation(cursor: _MySqlCursor) -> list[dict[str, Any]]:
            cursor.execute(TABLE_SCHEMA_SQL, (database, table))
            rows = cursor.fetchall()
            if not rows:
                raise TableNotFoundError(
                    f"Table '{table}' was not found in database '{database}'."
                )
            return [self._serialize_schema_row(row) for row in rows]

        return self._run_with_cursor(database, operation)

    def execute_query(self, database: str, sql: str, limit: int) -> QueryResult:
        def operation(cursor: _MySqlCursor) -> QueryResult:
            try:
                cursor.execute(sql)
            except _mysql_error_type() as exc:
                self._raise_for_mysql_error(exc, database=database)

            description = cursor.description or []
            columns = [str(item[0]) for item in description]
            fetched_rows = cursor.fetchmany(limit + 1)
            truncated = len(fetched_rows) > limit
            materialized_rows = [
                [self._normalize_value(value) for value in row]
                for row in fetched_rows[:limit]
            ]
            return QueryResult(
                columns=columns,
                rows=materialized_rows,
                row_count=len(materialized_rows),
                truncated=truncated,
            )

        return self._run_with_cursor(database, operation)

    def close(self) -> None:
        with self._connections_lock:
            connections = list(self._connections.values())
            self._connections.clear()
        for connection in connections:
            with closing(connection):
                pass

    def _run_with_cursor(
        self,
        database: str | None,
        operation: Callable[[_MySqlCursor], T],
    ) -> T:
        resolved_database = database or self._settings.default_database
        operation_lock = self._get_operation_lock(resolved_database)
        with operation_lock:
            try:
                with closing(self._get_connection(resolved_database).cursor()) as cursor:
                    return operation(cursor)
            except _mysql_error_type() as exc:
                if self._is_connection_error(exc):
                    self._discard_connection(resolved_database)
                    try:
                        with closing(
                            self._get_connection(resolved_database, force_new=True).cursor()
                        ) as cursor:
                            return operation(cursor)
                    except _mysql_error_type() as retry_exc:
                        self._raise_for_mysql_error(retry_exc, database=database)
                self._raise_for_mysql_error(exc, database=database)

    def _get_connection(
        self,
        database: str,
        *,
        force_new: bool = False,
    ) -> _MySqlConnection:
        with self._connections_lock:
            if force_new:
                self._discard_connection(database)
            connection = self._connections.get(database)
            if connection is not None:
                return connection
            connection = self._connect(database)
            self._connections[database] = connection
            return connection

    def _discard_connection(self, database: str) -> None:
        with self._connections_lock:
            connection = self._connections.pop(database, None)
        if connection is None:
            return
        with closing(connection):
            pass

    def _get_operation_lock(self, database: str) -> RLock:
        with self._connections_lock:
            lock = self._operation_locks.get(database)
            if lock is None:
                lock = RLock()
                self._operation_locks[database] = lock
            return lock

    def _connect(self, database: str) -> _MySqlConnection:
        _ensure_pymysql_available()
        try:
            raw_connection = cast(
                object,
                pymysql.connect(
                    host=self._settings.host,
                    port=self._settings.port,
                    user=self._settings.user,
                    password=self._settings.password,
                    database=database,
                    connect_timeout=self._settings.connect_timeout_seconds,
                    autocommit=True,
                    charset="utf8mb4",
                ),
            )
            if raw_connection is None:
                raise DatabaseConnectionError(
                    f"MySQL connection failed for database '{database}': pymysql.connect() returned None."
                )
            return _coerce_mysql_connection(raw_connection)
        except _mysql_error_type() as exc:
            self._raise_for_mysql_error(exc, database=database)

    def _raise_for_mysql_error(
        self,
        exc: Exception,
        *,
        database: str | None = None,
    ) -> NoReturn:
        code, message = _format_mysql_error(exc)
        lowered = message.lower()
        if code in DATABASE_NOT_FOUND_CODES:
            raise DatabaseNotFoundError(message) from exc
        if code in TABLE_NOT_FOUND_CODES or "doesn't exist" in lowered:
            raise TableNotFoundError(message) from exc
        if code in CONNECTION_ERROR_CODES:
            db_fragment = f" for database '{database}'" if database else ""
            raise DatabaseConnectionError(
                f"MySQL connection failed{db_fragment}: {message}"
            ) from exc
        if code in QUERY_ERROR_CODES:
            raise QueryExecutionError(message) from exc
        raise QueryExecutionError(message) from exc

    def _is_connection_error(self, exc: Exception) -> bool:
        code, _ = _format_mysql_error(exc)
        return code in CONNECTION_ERROR_CODES

    def _serialize_schema_row(self, row: _MySqlRow) -> dict[str, Any]:
        return {
            "column": str(row[0]),
            "type": str(row[1]),
            "nullable": bool(row[2]),
            "primary_key": bool(row[3]),
        }

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).hex()
        return value

def _format_mysql_error(exc: Exception) -> tuple[int, str]:
    code = 0
    if getattr(exc, "args", ()):
        first_arg = exc.args[0]
        if isinstance(first_arg, int):
            code = first_arg
    parts = [str(item).strip() for item in getattr(exc, "args", ()) if str(item).strip()]
    if not parts:
        return code, str(exc)
    return code, " | ".join(parts)


def probe_mysql_connectivity(
    settings: DatabaseSettings,
    *,
    timeout_seconds: int,
) -> dict[str, str]:
    client = MySqlClient(settings)
    _ensure_pymysql_available()
    try:
        raw_connection = cast(
            object,
            pymysql.connect(
                host=settings.host,
                port=settings.port,
                user=settings.user,
                password=settings.password,
                database=settings.default_database,
                connect_timeout=timeout_seconds,
                autocommit=True,
                charset="utf8mb4",
            ),
        )
        with closing(_coerce_mysql_connection(raw_connection)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(CONNECTIVITY_SQL)
                row = cursor.fetchone()
    except _mysql_error_type() as exc:
        _, message = _format_mysql_error(exc)
        raise RuntimeError(f"connectivity check failed: {message}") from exc

    if row is None:
        raise RuntimeError("connectivity check failed: MySQL returned no rows.")

    return {
        "server_name": str(row[0] or ""),
        "database_name": str(row[1] or ""),
        "login_name": str(row[2] or ""),
    }
