from __future__ import annotations

import json

import pytest

from LLM.pronunciation_overlay import apply_pronunciation_overlay
from LLM.selection_pipeline import (
    SelectionCandidate,
    SelectionDecision,
    SelectionPlan,
    SelectionResponseError,
    build_selection_plan,
    compose_selection,
    parse_selection_response,
    render_selection_response,
)
from LLM.stage4_preprocessor import preprocess_stage4
from LLM.stage5_preprocessor import preprocess_stage5


def test_stage4_plan_contains_code_renderable_natural_speech_choices() -> None:
    plan = build_selection_plan("현장에 있는 기자입니다.", stage=4)

    contraction = next(
        candidate
        for candidate in plan.candidates
        if candidate.kind == "natural_speech_contraction"
    )
    assert contraction.surface == "기자입니다"
    assert contraction.options == ("기잡니다",)
    assert all(candidate.candidate_id.startswith("S4-") for candidate in plan.candidates)
    assert any(candidate.kind == "prosody_comma" for candidate in plan.candidates)


def test_selection_response_is_strict_and_code_renders_final_text() -> None:
    plan = build_selection_plan("현장에 있는 기자입니다.", stage=4)
    contraction = next(
        candidate
        for candidate in plan.candidates
        if candidate.kind == "natural_speech_contraction"
    )
    response = json.dumps(
        {
            "schema_version": 1,
            "decisions": [{"id": contraction.candidate_id, "option": 0}],
        }
    )

    assert render_selection_response(
        "현장에 있는 기자입니다.", plan=plan, response_text=response
    ) == "현장에 있는 기잡니다."


@pytest.mark.parametrize(
    "response",
    (
        "not-json",
        '{"schema_version":1,"decisions":[{"id":"UNKNOWN","option":0}]}',
        '{"schema_version":1,"decisions":[{"id":"S4-0001","option":99}]}',
        '{"schema_version":1,"decisions":[],"extra":true}',
        '{"schema_version":1,"schema_version":1,"decisions":[]}',
    ),
)
def test_selection_response_rejects_unstructured_or_unauthorized_output(
    response: str,
) -> None:
    plan = SelectionPlan(
        (
            SelectionCandidate(
                "S4-0001", 0, 2, "test", "기자", ("기자",), "test"
            ),
        )
    )
    with pytest.raises(SelectionResponseError):
        parse_selection_response(response, plan=plan)


def test_ambiguous_acronym_may_be_preserved() -> None:
    plan = build_selection_plan("새 장비 XQZ를 도입했습니다.", stage=4)
    acronym = next(
        candidate
        for candidate in plan.candidates
        if candidate.kind == "residual_acronym"
    )
    assert acronym.required is False
    assert parse_selection_response('{"schema_version":1,"decisions":[]}', plan=plan) == ()


def test_code_composer_rejects_overlapping_selected_candidates() -> None:
    plan = SelectionPlan(
        (
            SelectionCandidate("S4-0001", 0, 2, "a", "가나", ("하나",), "a"),
            SelectionCandidate("S4-0002", 1, 3, "b", "나다", ("둘",), "b"),
        )
    )
    with pytest.raises(SelectionResponseError, match="overlapping"):
        compose_selection(
            "가나다",
            plan=plan,
            decisions=(
                SelectionDecision("S4-0001", 0),
                SelectionDecision("S4-0002", 0),
            ),
        )


def test_selection_plan_rejects_cross_stage_use() -> None:
    plan = build_selection_plan("현장에 있는 기자입니다.", stage=5)
    with pytest.raises(ValueError, match="another stage"):
        plan.validate_for_text("현장에 있는 기자입니다.", stage=4)


def test_stage4_preprocessor_does_not_apply_pronunciation_overlay() -> None:
    prepared = preprocess_stage4("상견례입니다.")

    assert prepared.text == "상견례입니다."
    combined = next(
        candidate
        for candidate in prepared.work_plan.candidates
        if "contraction" in candidate.kind
    )
    assert combined.kind == "natural_speech_contraction"
    assert combined.options == ('상견롑니다',)


def test_stage5_preprocessor_applies_overlay_then_locked_contraction() -> None:
    overlay = apply_pronunciation_overlay("상견례입니다.", stage=5)
    prepared = preprocess_stage5(overlay.text, snapshot=overlay.snapshot)

    assert prepared.text == "상견녜입니다."
    combined = next(
        candidate
        for candidate in prepared.work_plan.candidates
        if "contraction" in candidate.kind
    )
    assert combined.kind == "locked_natural_speech_contraction"
    assert combined.options == ("상견녭니다",)


def test_stage5_combines_locked_standard_pronunciation_and_contraction() -> None:
    prepared = preprocess_stage5("학교입니다.")

    assert prepared.text == "학꾜입니다."
    combined = next(
        candidate
        for candidate in prepared.work_plan.candidates
        if "contraction" in candidate.kind
    )
    assert combined.options == ("학꾭니다",)
    output = render_selection_response(
        prepared.text,
        plan=prepared.work_plan,
        response_text=json.dumps(
            {
                "schema_version": 1,
                "decisions": [{"id": combined.candidate_id, "option": 0}],
            }
        ),
    )
    assert output == "학꾭니다."


def test_stage5_plan_is_stage4_plan_superset_when_base_text_is_unchanged() -> None:
    text = "정부는 오늘 새로운 정책을 발표했습니다."
    level4 = build_selection_plan(text, stage=4)
    level5 = build_selection_plan(text, stage=5)

    signature = lambda candidate: (
        candidate.start,
        candidate.end,
        candidate.kind,
        candidate.surface,
        candidate.options,
    )
    assert {signature(item) for item in level4.candidates} <= {
        signature(item) for item in level5.candidates
    }


@pytest.mark.parametrize("prepare", (preprocess_stage4, preprocess_stage5))
@pytest.mark.parametrize(("source", "expected"), (
    ("3번 처리했습니다.", "세-번 처리했습니다."),
    ("3번 항목을 처리했습니다.", "삼번 항목을 처리했습니다."),
    ("3번을 처리했습니다.", "삼번을 처리했습니다."),
))
def test_levels4_and5_inherit_locked_beon_context(prepare, source, expected) -> None:
    prepared = prepare(source)
    assert prepared.text == expected
    assert not any(
        candidate.kind == "deferred_n_beon"
        for candidate in prepared.work_plan.candidates
    )
    assert any(
        span.provenance == "GENERATED_RESIDUAL_READING" and span.locked
        for span in prepared.snapshot.spans
    )


@pytest.mark.parametrize(("stage", "prepare"), (
    (4, preprocess_stage4),
    (5, preprocess_stage5),
))
def test_levels4_and5_keep_only_ambiguous_beon_for_llm(stage, prepare) -> None:
    prepared = prepare("3번 맡았습니다.")
    candidate = next(
        item for item in prepared.work_plan.candidates
        if item.kind == "deferred_n_beon"
    )
    assert candidate.candidate_id.startswith(f"S{stage}-")
    assert candidate.options == ("삼번", "세-번")
    assert "동작 서술어" in candidate.guidance


def test_prosody_plan_excludes_locked_leading_time_frame_boundary() -> None:
    plan = build_selection_plan(
        "올해 상반기 매출이 크게 늘었습니다.",
        stage=4,
    )
    assert not any(
        candidate.kind == "prosody_comma"
        and candidate.start == len("올해 상반기")
        for candidate in plan.candidates
    )
