from __future__ import annotations

import json
from pathlib import Path

import pytest

from LLM.config import (
    ConfigurationError,
    load_model_config,
    load_runtime_settings,
    PROMPT_PATH,
)


def test_model_config_has_fixed_models_and_default() -> None:
    config = load_model_config()

    assert config.models == ("gemma4:31b", "gemma4:26b", "gemma4:e4b")
    assert config.default_model == "gemma4:e4b"


def test_invalid_default_model_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    path.write_text(
        json.dumps({"models": ["gemma4:e4b"], "default_model": "unknown"}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="not in the model list"):
        load_model_config(path)


def test_runtime_settings_require_base_url_and_token(monkeypatch) -> None:
    monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LOCAL_LLM_TOKEN", raising=False)

    with pytest.raises(ConfigurationError, match="LOCAL_LLM_BASE_URL"):
        load_runtime_settings()


def test_runtime_settings_require_token(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.delenv("LOCAL_LLM_TOKEN", raising=False)

    with pytest.raises(ConfigurationError, match="LOCAL_LLM_TOKEN"):
        load_runtime_settings()


def test_prompt_template_is_stored_under_llm_docs() -> None:
    assert PROMPT_PATH == Path("LLM/docs/LLM_prompt.txt").resolve()
    assert PROMPT_PATH.is_file()
