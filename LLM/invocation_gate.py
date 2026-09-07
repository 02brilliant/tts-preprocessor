from __future__ import annotations

from dataclasses import dataclass

from LLM.selection_pipeline import SelectionPlan, build_selection_plan


@dataclass(frozen=True)
class LLMInvocationDecision:
    call_llm: bool
    reason: str


def decide_llm_invocation(
    normalized_text: str,
    *,
    stage_level: int,
    selection_plan: SelectionPlan | None = None,
    stage5_work_plan: SelectionPlan | None = None,
) -> LLMInvocationDecision:
    """Call a model only when the exact stage plan contains useful choices."""
    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be str")
    if isinstance(stage_level, bool) or stage_level not in {3, 4, 5}:
        raise ValueError("stage_level must be 3, 4, or 5")
    if selection_plan is not None and stage5_work_plan is not None:
        raise ValueError("selection_plan and stage5_work_plan are mutually exclusive")
    if stage5_work_plan is not None:
        if stage_level != 5:
            raise ValueError("stage5_work_plan is supported only for stage 5")
        selection_plan = stage5_work_plan
    active_plan = selection_plan or build_selection_plan(normalized_text, stage=stage_level)
    active_plan.validate_for_text(normalized_text, stage=stage_level)
    if not normalized_text.strip():
        return LLMInvocationDecision(False, "empty_rule_output")
    if not active_plan.has_candidates:
        # Retain the published stage-3 skip reason for existing consumers.
        return LLMInvocationDecision(False, "short_simple_rule_complete" if stage_level == 3 else f"stage{stage_level}_rule_complete")
    kinds = {candidate.kind for candidate in active_plan.candidates}
    if any(kind.startswith("residual_") or kind == "deferred_n_beon" for kind in kinds):
        return LLMInvocationDecision(True, "actionable_residue")
    if any("compound_boundary" in kind for kind in kinds):
        return LLMInvocationDecision(True, "compound_boundary_candidate")
    if kinds & {"natural_speech_contraction", "locked_natural_speech_contraction"}:
        return LLMInvocationDecision(True, "natural_speech_contraction_candidate")
    if "contextual_standard_pronunciation" in kinds:
        return LLMInvocationDecision(True, "korean_pronunciation_candidate")
    return LLMInvocationDecision(True, "prosody_or_structure_candidate" if stage_level == 3 else "natural_speech_candidate")


__all__ = ["LLMInvocationDecision", "decide_llm_invocation"]
