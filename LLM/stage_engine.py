from __future__ import annotations

from dataclasses import dataclass

from LLM.client import GenerationResult, generate
from LLM.config import (
    ConfigurationError,
    ModelConfig,
    load_gemini_settings,
    load_model_config,
    load_openai_settings,
    load_runtime_settings,
)
from LLM.gemini_client import generate_gemini
from LLM.openai_client import generate_openai
from LLM.prompt_template import build_prompt
from LLM.response_validation import validate_response


class UnsupportedLLMModelError(ValueError):
    """The requested model is not present in the packaged model registry."""


@dataclass(frozen=True)
class LLMStageResult:
    speech_text: str
    model: str
    elapsed_ms: float


def transform(normalized_text: str, *, model: str | None = None) -> LLMStageResult:
    """Run stage 2 from an already-normalized stage-1 string.

    This module deliberately has no dependency on ``engine`` or the stage-1
    binary. It builds the active prompt, invokes the selected provider, and
    accepts only a response that satisfies the stage-2 output contract.
    """

    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be str")
    if model is not None and not isinstance(model, str):
        raise TypeError("model must be str or None")

    model_config = load_model_config()
    selected_model = model or model_config.default_model
    definition = model_config.get(selected_model)
    if definition is None:
        raise UnsupportedLLMModelError("Unsupported LLM model.")

    prompt = build_prompt(normalized_text)
    result = _generate_with_provider(model_config, selected_model, prompt)
    return LLMStageResult(
        speech_text=validate_response(normalized_text, result.text),
        model=selected_model,
        elapsed_ms=result.elapsed_ms,
    )


def validate_runtime_assets() -> None:
    """Verify bundled prompt and model assets without calling an LLM."""

    load_model_config()
    build_prompt("")


def _generate_with_provider(
    model_config: ModelConfig,
    selected_model: str,
    prompt: str,
) -> GenerationResult:
    definition = model_config.get(selected_model)
    if definition is None:
        raise UnsupportedLLMModelError("Unsupported LLM model.")
    if definition.provider == "local":
        return generate(
            model=definition.upstream_model,
            prompt=prompt,
            settings=load_runtime_settings(),
        )
    if definition.provider == "gemini":
        return generate_gemini(
            model=definition.upstream_model,
            prompt=prompt,
            settings=load_gemini_settings(),
        )
    if definition.provider == "openai":
        return generate_openai(
            model=definition.upstream_model,
            prompt=prompt,
            settings=load_openai_settings(),
            reasoning_effort=definition.reasoning_effort,
        )
    raise ConfigurationError("Configured LLM provider is unsupported.")


__all__ = [
    "LLMStageResult",
    "UnsupportedLLMModelError",
    "transform",
    "validate_runtime_assets",
]
