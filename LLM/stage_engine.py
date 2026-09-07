from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import logging
import time

from LLM.client import GenerationResult, generate
from LLM.config import (
    ConfigurationError,
    ModelConfig,
    load_gemini_settings,
    load_model_config,
    load_openai_settings,
    load_runtime_settings,
    load_vllm_settings,
)
from LLM.gemini_client import generate_gemini
from LLM.openai_client import generate_openai
from LLM.prompt_template import build_prompt
from LLM.response_validation import LLMStageContractError, validate_response
from LLM.selection_pipeline import (
    SelectionPlan,
    build_selection_plan,
    recover_selection_response,
    compose_selection,
)
from LLM.validation_models import NormalizationSnapshot, ValidationIssue
from LLM.vllm_client import generate_vllm


class UnsupportedLLMModelError(ValueError):
    """The requested model is not present in the packaged model registry."""


@dataclass(frozen=True)
class LLMStageResult:
    speech_text: str
    model: str
    elapsed_ms: float
    validation_fallback: bool = False
    validation_issues: tuple[ValidationIssue, ...] = ()
    rejected_speech_text: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


_LOGGER = logging.getLogger(__name__)
Stage5WorkPlan = SelectionPlan


@dataclass(frozen=True)
class _BatchGenerationResult(GenerationResult):
    batches: tuple[tuple[SelectionPlan, str], ...] = ()


def transform(
    normalized_text: str,
    *,
    model: str | None = None,
    prompt_level: int = 1,
    snapshot: NormalizationSnapshot | None = None,
    selection_plan: SelectionPlan | None = None,
    stage5_work_plan: SelectionPlan | None = None,
) -> LLMStageResult:
    """Run one LLM stage from the level-2 normalized string.

    It uses engine reading helpers through the finite plan, never re-runs the
    rule engine or a stage binary, and accepts only structured selections.
    """

    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be str")
    if model is not None and not isinstance(model, str):
        raise TypeError("model must be str or None")
    if isinstance(prompt_level, bool) or prompt_level not in {1, 2, 3}:
        raise ValueError("prompt_level must be 1, 2, or 3")
    if selection_plan is not None and stage5_work_plan is not None:
        raise ValueError("selection_plan and stage5_work_plan are mutually exclusive")
    if stage5_work_plan is not None:
        selection_plan = stage5_work_plan
    if stage5_work_plan is not None and prompt_level != 3:
        raise ValueError("stage5_work_plan requires prompt_level=3")

    if selection_plan is None:
        selection_plan = build_selection_plan(
            normalized_text,
            stage=prompt_level + 2,
            snapshot=snapshot,
        )
    if selection_plan is not None:
        selection_plan.validate_for_text(
            normalized_text,
            stage=prompt_level + 2,
        )

    model_config = load_model_config()
    selected_model = model or model_config.default_model
    definition = model_config.get(selected_model)
    if definition is None:
        raise UnsupportedLLMModelError("Unsupported LLM model.")

    result = _generate_with_provider(
        model_config,
        selected_model,
        normalized_text,
        prompt_level=prompt_level,
        selection_plan=selection_plan,
    )
    batches = getattr(result, "batches", ()) or ((selection_plan, result.text),)
    accepted = []
    issues = []
    rejected = False
    for batch_plan, response in batches:
        decisions, invalid = recover_selection_response(response, plan=batch_plan)
        accepted.extend(decisions)
        rejected |= invalid
    # Conflicts may span two provider batches; validate globally as well.
    accepted, invalid = recover_selection_response(json.dumps({
        "schema_version": 1, "decisions": [
            {"id": d.candidate_id, "option": d.option} for d in accepted
        ],
    }), plan=selection_plan)
    rejected |= invalid
    if rejected:
        issues.append(ValidationIssue(
            "INVALID_SELECTION_RESPONSE", "High",
            "Invalid selections were restored to the pre-LLM base; valid selections were retained.",
        ))

    # Compose solely from code-owned options. Raw model output never becomes
    # speech, including on malformed JSON, invalid IDs, or fallback.
    retained = []
    speech_text = normalized_text
    for decision in sorted(accepted, key=lambda d: next(
        c.start for c in selection_plan.candidates if c.candidate_id == d.candidate_id
    )):
        tentative = compose_selection(
            normalized_text, plan=selection_plan,
            decisions=tuple(retained + [decision]),
        )
        try:
            validate_response(
                normalized_text, tentative, prompt_level=prompt_level,
                snapshot=snapshot, candidates=selection_plan.to_allowed_mutations(),
            )
        except LLMStageContractError as exc:
            if exc.severity != "Medium":
                rejected = True
                issues.append(ValidationIssue(exc.code, exc.severity, str(exc)))
                continue
        retained.append(decision)
        speech_text = tentative
    # Preserve existing Medium diagnostics without discarding approved edits.
    try:
        validate_response(
            normalized_text, speech_text, prompt_level=prompt_level,
            snapshot=snapshot, candidates=selection_plan.to_allowed_mutations(),
        )
    except LLMStageContractError as exc:
        issues.append(ValidationIssue(exc.code, exc.severity, str(exc)))
        if exc.severity != "Medium":
            speech_text = normalized_text
            rejected = True
    return LLMStageResult(
        speech_text=speech_text, model=selected_model,
        elapsed_ms=result.elapsed_ms, validation_fallback=rejected,
        validation_issues=tuple(issues),
        rejected_speech_text=result.text if rejected else None,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
    )


def validate_runtime_assets(*, prompt_levels: tuple[int, ...] = (1, 2, 3)) -> None:
    """Verify the requested bundled prompt and model assets without an LLM call."""

    load_model_config()
    if not prompt_levels or any(level not in {1, 2, 3} for level in prompt_levels):
        raise ValueError("prompt_levels must contain only 1, 2, or 3")
    for prompt_level in prompt_levels:
        build_prompt("", prompt_level=prompt_level)


def _generate_with_provider(
    model_config: ModelConfig,
    selected_model: str,
    normalized_text: str,
    *,
    prompt_level: int,
    selection_plan: SelectionPlan | None,
) -> GenerationResult:
    """Bound candidate payloads while retaining full document context and IDs."""
    if selection_plan is None or len(selection_plan.candidates) <= 96:
        return _generate_single(
            model_config,
            selected_model,
            normalized_text,
            prompt_level=prompt_level,
            selection_plan=selection_plan,
        )
    plans = [
        SelectionPlan(
            selection_plan.candidates[index : index + 96],
            stage=selection_plan.stage,
        )
        for index in range(0, len(selection_plan.candidates), 96)
    ]
    started = time.perf_counter()

    def run(plan):
        return _generate_single(
            model_config,
            selected_model,
            normalized_text,
            prompt_level=prompt_level,
            selection_plan=plan,
        )

    definition = model_config.get(selected_model)
    if definition is not None and definition.provider == "vllm":
        worker_count = min(
            load_vllm_settings().max_parallel_paragraphs,
            len(plans),
        )
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = list(executor.map(run, plans))
    else:
        results = [run(plan) for plan in plans]
    def total(field):
        values = [getattr(result, field) for result in results]
        return None if any(value is None for value in values) else sum(values)

    return _BatchGenerationResult(
        text=json.dumps([result.text for result in results], ensure_ascii=False),
        batches=tuple((plan, result.text) for plan, result in zip(plans, results)),
        elapsed_ms=(time.perf_counter() - started) * 1000,
        prompt_tokens=total("prompt_tokens"),
        completion_tokens=total("completion_tokens"),
    )


def _generate_single(
    model_config: ModelConfig,
    selected_model: str,
    normalized_text: str,
    *,
    prompt_level: int,
    selection_plan: SelectionPlan | None,
) -> GenerationResult:
    definition = model_config.get(selected_model)
    if definition is None:
        raise UnsupportedLLMModelError("Unsupported LLM model.")
    if definition.provider == "local":
        return generate(
            model=definition.upstream_model,
            prompt=build_prompt(
                normalized_text,
                prompt_level=prompt_level,
                selection_plan=selection_plan,
            ),
            settings=load_runtime_settings(),
        )
    if definition.provider == "gemini":
        return generate_gemini(
            model=definition.upstream_model,
            prompt=build_prompt(
                normalized_text,
                prompt_level=prompt_level,
                selection_plan=selection_plan,
            ),
            settings=load_gemini_settings(),
        )
    if definition.provider == "openai":
        return generate_openai(
            model=definition.upstream_model,
            prompt=build_prompt(
                normalized_text,
                prompt_level=prompt_level,
                selection_plan=selection_plan,
            ),
            settings=load_openai_settings(),
            reasoning_effort=definition.reasoning_effort,
        )
    if definition.provider == "vllm":
        return generate_vllm(
            model=definition.upstream_model,
            prompt=build_prompt(
                normalized_text,
                prompt_level=prompt_level,
                selection_plan=selection_plan,
            ),
            settings=load_vllm_settings(),
        )
    raise ConfigurationError("Configured LLM provider is unsupported.")



__all__ = [
    "LLMStageResult",
    "UnsupportedLLMModelError",
    "transform",
    "validate_runtime_assets",
]
