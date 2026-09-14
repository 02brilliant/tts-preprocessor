from __future__ import annotations

from dataclasses import dataclass

from LLM.pronunciation_overlay import (
    apply_pronunciation_overlay,
)
from LLM.provenance import minimal_snapshot
from LLM.residual_preprocessor import preprocess_residual
from LLM.selection_pipeline import (
    SelectionCandidate,
    SelectionPlan,
    build_selection_plan,
)
from LLM.validation_models import AllowedMutation, NormalizationSnapshot


Stage4Candidate = SelectionCandidate
Stage4WorkPlan = SelectionPlan


@dataclass(frozen=True)
class Stage4PreprocessResult:
    text: str
    snapshot: NormalizationSnapshot
    work_plan: SelectionPlan
    applied_mutations: tuple[AllowedMutation, ...] = ()


def preprocess_stage4(
    normalized_text: str,
    *,
    snapshot: NormalizationSnapshot | None = None,
) -> Stage4PreprocessResult:
    """Apply safe stage-4 readings and enumerate code-renderable choices."""

    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be str")
    active_snapshot = snapshot or minimal_snapshot(normalized_text)
    if active_snapshot.normalized_text != normalized_text:
        raise ValueError("snapshot does not match normalized_text")

    applied = apply_pronunciation_overlay(
        normalized_text,
        stage=4,
        snapshot=active_snapshot,
    )
    residual = preprocess_residual(applied.text, snapshot=applied.snapshot)
    work_plan = build_stage4_work_plan(residual.text, snapshot=residual.snapshot)
    return Stage4PreprocessResult(
        text=residual.text,
        snapshot=residual.snapshot,
        work_plan=work_plan,
        applied_mutations=applied.applied_mutations,
    )


def build_stage4_work_plan(
    stage4_base_text: str,
    *,
    snapshot: NormalizationSnapshot | None = None,
) -> SelectionPlan:
    return build_selection_plan(
        stage4_base_text,
        stage=4,
        snapshot=snapshot,
    )


__all__ = [
    "Stage4Candidate",
    "Stage4PreprocessResult",
    "Stage4WorkPlan",
    "build_stage4_work_plan",
    "preprocess_stage4",
]
