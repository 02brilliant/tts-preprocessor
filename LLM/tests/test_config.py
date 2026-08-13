from __future__ import annotations

import json
from pathlib import Path

import pytest

from LLM.config import (
    ConfigurationError,
    LLM_PROMPT_PATH,
    load_gemini_settings,
    load_model_config,
    load_openai_settings,
    load_runtime_settings,
    load_vllm_settings,
)


def test_model_config_has_fixed_models_and_default() -> None:
    config = load_model_config()

    assert config.models == (
        "gemma4:31b",
        "gemma4:26b",
        "gemma4:e4b",
        "gemma4-31B-it (vLLM)",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gpt-5.6-luna (medium)",
        "gpt-5.6-luna (low)",
        "gpt-5.6-luna (none)",
    )
    assert config.default_model == "gemma4:31b"
    assert config.get("gemma4:e4b").provider == "local"
    assert config.get("gemma4-31B-it (vLLM)").provider == "vllm"
    assert config.get("gemma4-31B-it (vLLM)").upstream_model == "google/gemma-4-31B-it"
    assert config.get("gemini-3.6-flash").provider == "gemini"
    assert config.get("gpt-5.6-luna (medium)").provider == "openai"
    assert config.get("gpt-5.6-luna (medium)").reasoning_effort == "medium"
    assert config.get("gpt-5.6-luna (low)").reasoning_effort == "low"
    assert config.get("gpt-5.6-luna (none)").reasoning_effort == "none"
    assert config.get("missing") is None


def test_invalid_default_model_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "id": "gemma4:e4b",
                        "provider": "local",
                        "upstream_model": "gemma4:e4b",
                    }
                ],
                "default_model": "unknown",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="not in the model list"):
        load_model_config(path)


def test_invalid_model_reasoning_effort_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "id": "gpt-test",
                        "provider": "openai",
                        "upstream_model": "gpt-5.6-luna",
                        "reasoning_effort": "minimal",
                    }
                ],
                "default_model": "gpt-test",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="model entry is invalid"):
        load_model_config(path)


@pytest.mark.parametrize("reasoning_effort", ([], {"value": "low"}, 1))
def test_non_string_model_reasoning_effort_is_rejected(
    tmp_path: Path,
    reasoning_effort,
) -> None:
    path = tmp_path / "models.json"
    path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "id": "gpt-test",
                        "provider": "openai",
                        "upstream_model": "gpt-5.6-luna",
                        "reasoning_effort": reasoning_effort,
                    }
                ],
                "default_model": "gpt-test",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="model entry is invalid"):
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


def test_gemini_settings_require_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="GEMINI_API_KEY"):
        load_gemini_settings()


def test_gemini_settings_load_key_and_timeout(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-test-key")
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "12.5")

    settings = load_gemini_settings()

    assert settings.api_key == "dummy-gemini-test-key"
    assert settings.timeout_seconds == 12.5


def test_vllm_settings_require_base_url_and_token(monkeypatch) -> None:
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("VLLM_TOKEN", raising=False)

    with pytest.raises(ConfigurationError, match="VLLM_BASE_URL"):
        load_vllm_settings()


def test_vllm_settings_require_token(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.invalid/v1")
    monkeypatch.delenv("VLLM_TOKEN", raising=False)

    with pytest.raises(ConfigurationError, match="VLLM_TOKEN"):
        load_vllm_settings()


def test_vllm_settings_load_base_url_token_and_timeout(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.invalid/v1/")
    monkeypatch.setenv("VLLM_TOKEN", "dummy-vllm-test-token")
    monkeypatch.setenv("VLLM_TIMEOUT_SECONDS", "45.5")
    monkeypatch.delenv("VLLM_MAX_PARALLEL_PARAGRAPHS", raising=False)

    settings = load_vllm_settings()

    assert settings.base_url == "http://vllm.invalid/v1"
    assert settings.token == "dummy-vllm-test-token"
    assert settings.timeout_seconds == 45.5
    assert settings.max_parallel_paragraphs == 8


def test_vllm_settings_load_max_parallel_paragraphs(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.invalid/v1")
    monkeypatch.setenv("VLLM_TOKEN", "dummy-vllm-test-token")
    monkeypatch.setenv("VLLM_MAX_PARALLEL_PARAGRAPHS", "4")

    settings = load_vllm_settings()

    assert settings.max_parallel_paragraphs == 4


def test_vllm_settings_reject_invalid_max_parallel_paragraphs(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.invalid/v1")
    monkeypatch.setenv("VLLM_TOKEN", "dummy-vllm-test-token")
    monkeypatch.setenv("VLLM_MAX_PARALLEL_PARAGRAPHS", "0")

    with pytest.raises(ConfigurationError, match="VLLM_MAX_PARALLEL_PARAGRAPHS"):
        load_vllm_settings()


def test_openai_settings_require_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        load_openai_settings()


def test_openai_settings_load_defaults(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-openai-test-key")
    monkeypatch.delenv("OPENAI_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("OPENAI_REASONING_EFFORT", raising=False)

    settings = load_openai_settings()

    assert settings.api_key == "dummy-openai-test-key"
    assert settings.timeout_seconds == 300
    assert settings.reasoning_effort == "medium"


def test_openai_settings_load_timeout_and_reasoning_effort(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-openai-test-key")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "45.5")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "low")

    settings = load_openai_settings()

    assert settings.timeout_seconds == 45.5
    assert settings.reasoning_effort == "low"


def test_openai_settings_reject_invalid_reasoning_effort(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-openai-test-key")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "minimal")

    with pytest.raises(ConfigurationError, match="OPENAI_REASONING_EFFORT"):
        load_openai_settings()


def test_integrated_prompt_template_is_stored_under_llm_docs() -> None:
    assert LLM_PROMPT_PATH == Path("LLM/docs/LLM_prompt.txt").resolve()
    assert LLM_PROMPT_PATH.is_file()


def test_deprecated_stage_prompts_are_not_runtime_dependencies() -> None:
    runtime_sources = (
        Path("LLM/config.py"),
        Path("LLM/prompt_template.py"),
        Path("api/server.py"),
        Path("LLM/tests/smoke_gemini.py"),
        Path("LLM/tests/smoke_openai.py"),
        Path("LLM/tests/smoke_vllm.py"),
    )

    for source_path in runtime_sources:
        source = source_path.read_text(encoding="utf-8")
        assert "LLM_prompt_prosody.txt" not in source
        assert "LLM_prompt_speech.txt" not in source
