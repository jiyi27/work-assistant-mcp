from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool


class DatabaseClientError(RuntimeError):
    """Base class for expected database client failures."""


class DatabaseConnectionError(DatabaseClientError):
    """Database connection, authentication, or driver setup failure."""


class DatabaseNotFoundError(DatabaseClientError):
    """Requested database was not found or not accessible."""


class TableNotFoundError(DatabaseClientError):
    """Requested table was not found."""


class QueryExecutionError(DatabaseClientError):
    """SQL query failed in a way the caller may be able to fix."""


class AbstractDatabaseClient(ABC):
    @abstractmethod
    def list_databases(self) -> list[str]:
        """Return databases visible to the configured account."""

    @abstractmethod
    def list_tables(self, database: str) -> list[str]:
        """Return tables in the requested database."""

    @abstractmethod
    def get_table_schema(self, database: str, table: str) -> list[dict[str, Any]]:
        """Return table schema details."""

    @abstractmethod
    def execute_query(self, database: str, sql: str) -> QueryResult:
        """Execute a validated read-only query."""
