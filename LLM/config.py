from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path


MODEL_CONFIG_PATH = Path(__file__).resolve().parent / "models.json"
PROMPT_PATH = Path(__file__).resolve().parent / "docs" / "LLM_prompt.txt"


class ConfigurationError(ValueError):
    """Raised when proxy configuration is missing or malformed."""


@dataclass(frozen=True)
class ModelConfig:
    models: tuple[str, ...]
    default_model: str


@dataclass(frozen=True)
class RuntimeSettings:
    base_url: str
    token: str
    timeout_seconds: float


def load_model_config(path: Path = MODEL_CONFIG_PATH) -> ModelConfig:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError("LLM model configuration file is missing.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("LLM model configuration is invalid.") from exc

    if not isinstance(payload, dict):
        raise ConfigurationError("LLM model configuration must be an object.")

    models = payload.get("models")
    default_model = payload.get("default_model")
    if (
        not isinstance(models, list)
        or not models
        or any(not isinstance(model, str) or not model.strip() for model in models)
    ):
        raise ConfigurationError("LLM model list is invalid.")
    if len(set(models)) != len(models):
        raise ConfigurationError("LLM model list contains duplicates.")
    if not isinstance(default_model, str) or default_model not in models:
        raise ConfigurationError("Default LLM model is not in the model list.")

    return ModelConfig(models=tuple(models), default_model=default_model)


def load_runtime_settings() -> RuntimeSettings:
    base_url = os.getenv("LOCAL_LLM_BASE_URL", "").strip()
    token = os.getenv("LOCAL_LLM_TOKEN", "").strip()
    if not base_url:
        raise ConfigurationError("Required environment variable LOCAL_LLM_BASE_URL is missing.")
    if not token:
        raise ConfigurationError("Required environment variable LOCAL_LLM_TOKEN is missing.")

    timeout_raw = os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "300").strip()
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise ConfigurationError("LOCAL_LLM_TIMEOUT_SECONDS must be a number.") from exc
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ConfigurationError("LOCAL_LLM_TIMEOUT_SECONDS must be greater than zero.")

    return RuntimeSettings(
        base_url=base_url.rstrip("/"),
        token=token,
        timeout_seconds=timeout_seconds,
    )
