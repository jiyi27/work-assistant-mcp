from __future__ import annotations

import sqlparse
from sqlparse import tokens as ttypes
from sqlparse.sql import Statement, Token


class ReadOnlyViolation(ValueError):
    """Query was rejected by best-effort read-only validation."""


def validate_read_only_query(sql: str) -> None:
    statements = [item for item in sqlparse.parse(sql) if item.tokens]
    if len(statements) != 1:
        raise ReadOnlyViolation(
            "Only a single statement per call is allowed. Remove the semicolon and retry with one SELECT statement."
        )

    statement = statements[0]
    if statement.get_type() != "SELECT":
        raise ReadOnlyViolation(
            "Only SELECT statements are allowed. Remove the non-SELECT statement and retry."
        )

    if _contains_select_into(statement):
        raise ReadOnlyViolation(
            "SELECT INTO is not allowed because it can create tables. Remove the INTO clause and retry."
        )


def _contains_select_into(statement: Statement) -> bool:
    saw_select = False
    for token in statement.flatten():
        if token.is_whitespace or token.ttype in ttypes.Comment:
            continue
        if _is_keyword(token, "SELECT"):
            saw_select = True
            continue
        if saw_select and _is_keyword(token, "INTO"):
            return True
    return False


def _is_keyword(token: Token, normalized: str) -> bool:
    return token.ttype in ttypes.Keyword and token.normalized == normalized
