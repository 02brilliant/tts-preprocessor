from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time

from LLM.client import GenerationResult, generate
from LLM.config import (
    ConfigurationError,
    ModelConfig,
    VllmSettings,
    load_gemini_settings,
    load_model_config,
    load_openai_settings,
    load_runtime_settings,
    load_vllm_settings,
)
from LLM.gemini_client import generate_gemini
from LLM.openai_client import generate_openai
from LLM.paragraph_parallel import join_paragraph_units, split_paragraph_units
from LLM.prompt_template import build_prompt
from LLM.response_validation import validate_response
from LLM.vllm_client import generate_vllm


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

    result = _generate_with_provider(model_config, selected_model, normalized_text)
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
    normalized_text: str,
) -> GenerationResult:
    definition = model_config.get(selected_model)
    if definition is None:
        raise UnsupportedLLMModelError("Unsupported LLM model.")
    if definition.provider == "local":
        return generate(
            model=definition.upstream_model,
            prompt=build_prompt(normalized_text),
            settings=load_runtime_settings(),
        )
    if definition.provider == "gemini":
        return generate_gemini(
            model=definition.upstream_model,
            prompt=build_prompt(normalized_text),
            settings=load_gemini_settings(),
        )
    if definition.provider == "openai":
        return generate_openai(
            model=definition.upstream_model,
            prompt=build_prompt(normalized_text),
            settings=load_openai_settings(),
            reasoning_effort=definition.reasoning_effort,
        )
    if definition.provider == "vllm":
        return _generate_vllm_paragraphs(
            model=definition.upstream_model,
            normalized_text=normalized_text,
            settings=load_vllm_settings(),
        )
    raise ConfigurationError("Configured LLM provider is unsupported.")


def _generate_vllm_paragraphs(
    *,
    model: str,
    normalized_text: str,
    settings: VllmSettings,
) -> GenerationResult:
    chunks, separators = split_paragraph_units(normalized_text)
    work_items = [
        (index, chunk)
        for index, chunk in enumerate(chunks)
        if chunk.strip()
    ]
    if len(work_items) <= 1:
        return generate_vllm(
            model=model,
            prompt=build_prompt(normalized_text),
            settings=settings,
        )

    outputs = list(chunks)
    started_at = time.perf_counter()
    max_workers = min(settings.max_parallel_paragraphs, len(work_items))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                generate_vllm,
                model=model,
                prompt=build_prompt(chunk),
                settings=settings,
            ): index
            for index, chunk in work_items
        }
        try:
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                outputs[index] = future.result().text
        except BaseException:
            for future in future_to_index:
                future.cancel()
            raise

    return GenerationResult(
        text=join_paragraph_units(tuple(outputs), separators),
        elapsed_ms=(time.perf_counter() - started_at) * 1000,
    )


__all__ = [
    "LLMStageResult",
    "UnsupportedLLMModelError",
    "transform",
    "validate_runtime_assets",
]
