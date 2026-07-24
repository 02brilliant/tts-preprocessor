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
class ModelDefinition:
    id: str
    provider: str
    upstream_model: str


@dataclass(frozen=True)
class ModelConfig:
    definitions: tuple[ModelDefinition, ...]
    default_model: str

    @property
    def models(self) -> tuple[str, ...]:
        return tuple(definition.id for definition in self.definitions)

    def get(self, model_id: str) -> ModelDefinition | None:
        return next(
            (
                definition
                for definition in self.definitions
                if definition.id == model_id
            ),
            None,
        )


@dataclass(frozen=True)
class RuntimeSettings:
    base_url: str
    token: str
    timeout_seconds: float


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str
    timeout_seconds: float


def _load_positive_timeout(environment_name: str, default: str = "300") -> float:
    timeout_raw = os.getenv(environment_name, default).strip()
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise ConfigurationError(f"{environment_name} must be a number.") from exc
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ConfigurationError(f"{environment_name} must be greater than zero.")
    return timeout_seconds


def load_model_config(path: Path = MODEL_CONFIG_PATH) -> ModelConfig:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError("LLM model configuration file is missing.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("LLM model configuration is invalid.") from exc

    if not isinstance(payload, dict):
        raise ConfigurationError("LLM model configuration must be an object.")

    models_payload = payload.get("models")
    default_model = payload.get("default_model")
    if not isinstance(models_payload, list) or not models_payload:
        raise ConfigurationError("LLM model list is invalid.")

    definitions: list[ModelDefinition] = []
    for model_payload in models_payload:
        if not isinstance(model_payload, dict):
            raise ConfigurationError("LLM model entry is invalid.")
        model_id = model_payload.get("id")
        provider = model_payload.get("provider")
        upstream_model = model_payload.get("upstream_model")
        if (
            not isinstance(model_id, str)
            or not model_id.strip()
            or provider not in {"local", "gemini"}
            or not isinstance(upstream_model, str)
            or not upstream_model.strip()
        ):
            raise ConfigurationError("LLM model entry is invalid.")
        definitions.append(
            ModelDefinition(
                id=model_id,
                provider=provider,
                upstream_model=upstream_model,
            )
        )

    model_ids = tuple(definition.id for definition in definitions)
    if len(set(model_ids)) != len(model_ids):
        raise ConfigurationError("LLM model list contains duplicates.")
    if not isinstance(default_model, str) or default_model not in model_ids:
        raise ConfigurationError("Default LLM model is not in the model list.")

    return ModelConfig(
        definitions=tuple(definitions),
        default_model=default_model,
    )


def load_runtime_settings() -> RuntimeSettings:
    base_url = os.getenv("LOCAL_LLM_BASE_URL", "").strip()
    token = os.getenv("LOCAL_LLM_TOKEN", "").strip()
    if not base_url:
        raise ConfigurationError(
            "Required environment variable LOCAL_LLM_BASE_URL is missing."
        )
    if not token:
        raise ConfigurationError(
            "Required environment variable LOCAL_LLM_TOKEN is missing."
        )

    return RuntimeSettings(
        base_url=base_url.rstrip("/"),
        token=token,
        timeout_seconds=_load_positive_timeout("LOCAL_LLM_TIMEOUT_SECONDS"),
    )


def load_gemini_settings() -> GeminiSettings:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            "Required environment variable GEMINI_API_KEY is missing."
        )
    return GeminiSettings(
        api_key=api_key,
        timeout_seconds=_load_positive_timeout("GEMINI_TIMEOUT_SECONDS"),
    )
