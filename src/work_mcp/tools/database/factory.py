from __future__ import annotations

from ...config import DatabaseSettings
from .base import AbstractDatabaseClient
from .sqlserver import SqlServerClient

SUPPORTED_DB_TYPES = frozenset({"sqlserver"})


def get_db_client(config: DatabaseSettings) -> AbstractDatabaseClient:
    if config.db_type == "sqlserver":
        return SqlServerClient(config)
    raise ValueError(f"Unsupported db_type: {config.db_type!r}")
