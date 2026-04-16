from __future__ import annotations

import sqlparse
from sqlparse import tokens as ttypes
from sqlparse.sql import Statement, Token

DISALLOWED_SEQUENCE_MESSAGES: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("FOR", "UPDATE"),
        "SELECT ... FOR UPDATE is not allowed because it can acquire write-intent locks. Remove the locking clause and retry.",
    ),
    (
        ("LOCK", "IN", "SHARE", "MODE"),
        "LOCK IN SHARE MODE is not allowed because it can acquire shared locks. Remove the locking clause and retry.",
    ),
    (
        ("WAITFOR",),
        "WAITFOR is not allowed because this inspection tool must not block execution deliberately. Remove WAITFOR and retry.",
    ),
)

DISALLOWED_LOCK_HINTS = frozenset({"UPDLOCK", "XLOCK", "HOLDLOCK"})


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

    disallowed_message = _find_disallowed_sequence(statement)
    if disallowed_message is not None:
        raise ReadOnlyViolation(disallowed_message)

    if _contains_disallowed_lock_hint(statement):
        raise ReadOnlyViolation(
            "SQL Server lock hints such as UPDLOCK, XLOCK, or HOLDLOCK are not allowed because they can change locking behavior. Remove the lock hint and retry."
        )


def _contains_select_into(statement: Statement) -> bool:
    saw_select = False
    for token in _meaningful_tokens(statement):
        if token.is_whitespace or token.ttype in ttypes.Comment:
            continue
        if _is_keyword(token, "SELECT"):
            saw_select = True
            continue
        if saw_select and _is_keyword(token, "INTO"):
            return True
    return False


def _find_disallowed_sequence(statement: Statement) -> str | None:
    normalized_tokens = [token.normalized for token in _meaningful_tokens(statement)]
    for sequence, message in DISALLOWED_SEQUENCE_MESSAGES:
        sequence_length = len(sequence)
        for index in range(len(normalized_tokens) - sequence_length + 1):
            if tuple(normalized_tokens[index:index + sequence_length]) == sequence:
                return message
    return None


def _contains_disallowed_lock_hint(statement: Statement) -> bool:
    normalized_tokens = [token.normalized for token in _meaningful_tokens(statement)]
    for index in range(len(normalized_tokens) - 3):
        if normalized_tokens[index:index + 2] != ["WITH", "("]:
            continue
        hint_tokens: list[str] = []
        for token in normalized_tokens[index + 2:]:
            if token == ")":
                break
            hint_tokens.append(token)
        if any(token in DISALLOWED_LOCK_HINTS for token in hint_tokens):
            return True
    return False


def _meaningful_tokens(statement: Statement) -> list[Token]:
    return [
        token
        for token in statement.flatten()
        if not token.is_whitespace and token.ttype not in ttypes.Comment
    ]


def _is_keyword(token: Token, normalized: str) -> bool:
    return token.ttype in ttypes.Keyword and token.normalized == normalized
