from __future__ import annotations

from dataclasses import dataclass

from LLM.provenance import minimal_snapshot
from LLM.residual_preprocessor import preprocess_residual
from LLM.selection_pipeline import SelectionPlan, build_selection_plan
from LLM.validation_models import NormalizationSnapshot


@dataclass(frozen=True)
class Stage3PreprocessResult:
    text: str
    snapshot: NormalizationSnapshot
    work_plan: SelectionPlan


def preprocess_stage3(
    text: str,
    *,
    snapshot: NormalizationSnapshot | None = None,
) -> Stage3PreprocessResult:
    applied = preprocess_residual(text, snapshot=snapshot or minimal_snapshot(text))
    return Stage3PreprocessResult(
        applied.text,
        applied.snapshot,
        build_selection_plan(
            applied.text,
            stage=3,
            snapshot=applied.snapshot,
        ),
    )
