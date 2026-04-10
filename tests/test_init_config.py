from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "init_config.py"


def _load_init_config_module():
    spec = importlib.util.spec_from_file_location("test_init_config_module", _MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collect_jira_config_skips_prompts_when_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_init_config_module()

    def fail_collect(*args, **kwargs):
        raise AssertionError("_collect_field_values should not be called for complete config")

    monkeypatch.setattr(module, "_collect_field_values", fail_collect)

    result = module.collect_jira_config(
        {
            "base_url": "https://jira.example.invalid",
            "api_token": "secret-token",
            "project_key": "IOS",
        }
    )

    assert result == {
        "jira_base_url": "https://jira.example.invalid",
        "jira_api_token": "secret-token",
        "jira_project_key": "IOS",
    }


def test_collect_jira_config_reprompts_when_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_init_config_module()
    expected = {
        "jira_base_url": "https://new.example.invalid",
        "jira_api_token": "new-token",
        "jira_project_key": "NEW",
    }

    monkeypatch.setattr(module, "_collect_field_values", lambda *args, **kwargs: expected)

    result = module.collect_jira_config(
        {
            "base_url": None,
            "api_token": "secret-token",
            "project_key": "IOS",
        }
    )

    assert result == expected


def test_collect_log_search_config_skips_prompts_when_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_init_config_module()

    def fail_collect(*args, **kwargs):
        raise AssertionError("_collect_field_values should not be called for complete config")

    monkeypatch.setattr(module, "_collect_field_values", fail_collect)

    result = module.collect_log_search_config(
        {"log_search": {"log_base_dir": "/tmp/work-logs"}}
    )

    assert result == {"log_base_dir": "/tmp/work-logs"}


def test_collect_log_search_config_reprompts_when_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_init_config_module()
    expected = {"log_base_dir": "/tmp/new-logs"}

    monkeypatch.setattr(module, "_collect_field_values", lambda *args, **kwargs: expected)

    result = module.collect_log_search_config({"log_search": {"log_base_dir": None}})

    assert result == expected
