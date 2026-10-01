from __future__ import annotations

from dataclasses import replace

import pytest

from LLM.provenance import build_normalization_snapshot
from LLM.selection_pipeline import build_selection_plan
from LLM.response_validation import LLMStageContractError, validate_response
from engine.span_engine.transform import transform_with_trace


def test_snapshot_projects_generated_readings_to_normalized_coordinates() -> None:
    output = transform_with_trace("AI는 3kg이다.")
    snapshot = build_normalization_snapshot(output)

    locked = [span for span in snapshot.spans if span.locked and not span.protected]
    assert locked
    for span in locked:
        assert snapshot.normalized_text[span.normalized_start:span.normalized_end] == span.text
    assert any("에이아이" in span.text for span in locked)
    assert any("삼-킬로그램" in span.text for span in locked)


def test_snapshot_marks_canonical_protected_literals() -> None:
    output = transform_with_trace("주소는 https://example.com/a1 입니다.")
    snapshot = build_normalization_snapshot(output)
    protected = [span for span in snapshot.spans if span.protected]
    assert [span.text for span in protected] == ["https://example.com/a1"]


@pytest.mark.parametrize("intro", ["회의는 (오늘) 시작한다. ", "회의는 시작한다.\n"])
@pytest.mark.parametrize("stage", [3, 4])
def test_repeated_readings_keep_locks_after_presentation_edits(intro, stage):
    text = (intro + "2~5명이 2.50kg을 옮겼고 52,025원과 3/4만큼을 기록했다. ") * 10
    output = transform_with_trace(text)
    snapshot = build_normalization_snapshot(output)
    generated = [piece for piece in output.render_pieces if piece.text
                 and piece.provenance in {"GENERATED_READING", "GENERATED_PARTICLE", "GENERATED_PUNCT"}]
    locked = [span for span in snapshot.spans if span.locked and not span.protected]
    assert len(locked) == len(generated) == 80
    assert [span.text for span in locked] == [piece.text for piece in generated]
    assert len(snapshot.numeric_annotations) == 40
    assert all(annotation.alignment == "exact" for annotation in snapshot.numeric_annotations)
    plan = build_selection_plan(output.normalized_text, stage=stage, snapshot=snapshot)
    assert all(not any(candidate.start < span.normalized_end and span.normalized_start < candidate.end
                       for span in locked) for candidate in plan.candidates)
    speech = output.normalized_text.replace("오~만 이~천이십오-원", "오~만, 이~천이십오-원", 1)
    with pytest.raises(LLMStageContractError):
        validate_response(output.normalized_text, speech, prompt_level=1 if stage == 3 else 3,
                          snapshot=snapshot, candidates=plan.to_allowed_mutations())


@pytest.mark.parametrize("source", ["2개", "2개이다"])
def test_untraceable_edit_cannot_silently_discard_generated_lock(source):
    output = transform_with_trace(source)
    unknown = replace(output, normalized_text="앞말 " + output.normalized_text)
    snapshot = build_normalization_snapshot(unknown)
    assert any(span.locked and span.provenance == "ALIGNMENT_UNRESOLVED"
               and span.text == unknown.normalized_text for span in snapshot.spans)
    assert not build_selection_plan(unknown.normalized_text, stage=4, snapshot=snapshot).candidates
    assert all(annotation.output_span is None for annotation in snapshot.numeric_annotations)
