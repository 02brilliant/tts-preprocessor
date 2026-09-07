from __future__ import annotations

from dataclasses import dataclass

from LLM.pronunciation_lexicon import (
    build_stage5_deterministic_pronunciation_mutations,
)
from LLM.pronunciation_overlay import (
    PronunciationOverlayResult,
    apply_locked_pronunciation_mutations,
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
    stage4_base_text: str,
    *,
    snapshot: NormalizationSnapshot | None = None,
) -> Stage5PreprocessResult:
    """Apply safe stage-5 readings and enumerate code-renderable choices."""

    if not isinstance(stage4_base_text, str):
        raise TypeError("stage4_base_text must be str")
    active_snapshot = snapshot or minimal_snapshot(stage4_base_text)
    if active_snapshot.normalized_text != stage4_base_text:
        raise ValueError("snapshot does not match stage4_base_text")

    # Stage 5 may complete a stage-4 partial pronunciation (for example,
    # 색년필 -> 생년필), but it must still respect every protected span and
    # every lock owned by the rule engine or another subsystem.
    eligibility_snapshot = NormalizationSnapshot(
        normalized_text=active_snapshot.normalized_text,
        spans=tuple(
            span
            for span in active_snapshot.spans
            if span.provenance != "GENERATED_STAGE4_PRONUNCIATION"
        ),
    )
    deterministic = build_stage5_deterministic_pronunciation_mutations(
        stage4_base_text,
        snapshot=eligibility_snapshot,
    )
    applied: PronunciationOverlayResult = apply_locked_pronunciation_mutations(
        stage4_base_text,
        mutations=deterministic,
        snapshot=active_snapshot,
        owner="stage5_standard_pronunciation",
        provenance="GENERATED_STAGE5_PRONUNCIATION",
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
