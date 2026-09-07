from __future__ import annotations

from dataclasses import dataclass

from LLM.provenance import minimal_snapshot
from LLM.residual_preprocessor import preprocess_residual
from LLM.selection_pipeline import SelectionPlan, build_selection_plan
from LLM.validation_models import NormalizationSnapshot


@dataclass(frozen=True)
class Stage4PreprocessResult:
    text: str
    snapshot: NormalizationSnapshot
    work_plan: SelectionPlan


def preprocess_stage4(
    stage4_base_text: str,
    *,
    snapshot: NormalizationSnapshot | None = None,
) -> Stage4PreprocessResult:
    if not isinstance(stage4_base_text, str):
        raise TypeError("stage4_base_text must be str")
    active_snapshot = snapshot or minimal_snapshot(stage4_base_text)
    if active_snapshot.normalized_text != stage4_base_text:
        raise ValueError("snapshot does not match stage4_base_text")
    residual = preprocess_residual(stage4_base_text, snapshot=active_snapshot)
    stage4_base_text, active_snapshot = residual.text, residual.snapshot
    return Stage4PreprocessResult(
        text=stage4_base_text,
        snapshot=active_snapshot,
        work_plan=build_selection_plan(
            stage4_base_text,
            stage=4,
            snapshot=active_snapshot,
        ),
    )


__all__ = ["Stage4PreprocessResult", "preprocess_stage4"]
