from __future__ import annotations


INTERNAL_ERROR_RETRY_HINT = (
    "An internal error occurred. Retry up to 2 times; "
    "if still failing, stop and notify the user with the message above."
)
DINGTALK_INTERNAL_ERROR_HINT = (
    "An internal error occurred. Stop and tell the user in your reply: "
    "the notification could not be sent."
)


def required_param_hint(param_name: str) -> str:
    return f"`{param_name}` must not be empty. Fix the parameter and retry."


def jira_issue_not_found_hint(issue_key: str) -> str:
    return (
        f"Issue {issue_key} was not found. "
        "Only retry with a different key if you are certain you used the wrong one; "
        "do not guess. Otherwise stop and notify the user."
    )


JIRA_TRANSITION_FAILURE_HINT = (
    "The Jira workflow change could not be completed. Stop execution, summarize what you completed, "
    "and notify the user with the current status, target status, and available target statuses."
)


def jira_project_not_allowed_hint(issue_key: str) -> str:
    return (
        f"{issue_key} is outside the configured Jira project scope. "
        "Do not retry this write operation. Stop and notify the user."
    )


def jira_assignee_not_allowed_hint(issue_key: str) -> str:
    return (
        f"{issue_key} is not currently assigned to you. "
        "Do not retry this write operation unless the issue is reassigned to you. "
        "Stop and notify the user."
    )


def jira_attachment_not_found_hint(issue_key: str, attachment_id: str) -> str:
    return (
        f"Attachment {attachment_id} was not found on {issue_key}, or it is not a supported image attachment. "
        "Do not guess another attachment id. Stop and notify the user."
    )
