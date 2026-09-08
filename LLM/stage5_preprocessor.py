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


Stage5Candidate = SelectionCandidate
Stage5WorkPlan = SelectionPlan


@dataclass(frozen=True)
class Stage5PreprocessResult:
    text: str
    snapshot: NormalizationSnapshot
    work_plan: SelectionPlan
    applied_mutations: tuple[AllowedMutation, ...] = ()


def preprocess_stage5(
    normalized_text: str,
    *,
    snapshot: NormalizationSnapshot | None = None,
) -> Stage5PreprocessResult:
    """Apply safe stage-5 readings and enumerate code-renderable choices."""

    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be str")
    active_snapshot = snapshot or minimal_snapshot(normalized_text)
    if active_snapshot.normalized_text != normalized_text:
        raise ValueError("snapshot does not match normalized_text")

    applied = apply_pronunciation_overlay(
        normalized_text,
        stage=5,
        snapshot=active_snapshot,
    )
    residual = preprocess_residual(applied.text, snapshot=applied.snapshot)
    work_plan = build_stage5_work_plan(residual.text, snapshot=residual.snapshot)
    return Stage5PreprocessResult(
        text=residual.text,
        snapshot=residual.snapshot,
        work_plan=work_plan,
        applied_mutations=applied.applied_mutations,
    )


def build_stage5_work_plan(
    stage5_base_text: str,
    *,
    snapshot: NormalizationSnapshot | None = None,
) -> SelectionPlan:
    return build_selection_plan(
        stage5_base_text,
        stage=5,
        snapshot=snapshot,
    )


__all__ = [
    "Stage5Candidate",
    "Stage5PreprocessResult",
    "Stage5WorkPlan",
    "build_stage5_work_plan",
    "preprocess_stage5",
]
