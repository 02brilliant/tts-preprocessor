from __future__ import annotations

import json

from LLM.pronunciation_overlay import apply_pronunciation_overlay
from LLM.provenance import minimal_snapshot
from LLM.stage5_preprocessor import (
    Stage5Candidate,
    Stage5WorkPlan,
    build_stage5_work_plan,
    preprocess_stage5,
)


def test_stage5_preprocessor_applies_safe_standard_pronunciations_and_locks() -> None:
    stage4 = apply_pronunciation_overlay(
        "색연필과 국물, 인기는 높고 학교는 멉니다.",
        stage=4,
    )
    result = preprocess_stage5(stage4.text, snapshot=stage4.snapshot)

    assert stage4.text == "색년필과 국물, 인기는 높고 학교는 멉니다."
    assert result.text == "생년필과 궁물, 인끼는 높고 학꾜는 멉니다."
    locked = {
        span.text
        for span in result.snapshot.spans
        if span.provenance == "GENERATED_STAGE5_PRONUNCIATION" and span.locked
    }
    assert locked == {"생년필", "궁물", "인끼", "학꾜"}


def test_stage5_preprocessor_keeps_longer_words_and_protected_surfaces() -> None:
    text = "개인기와 무인기, https://example.com/국물/학교"
    result = preprocess_stage5(text, snapshot=minimal_snapshot(text))

    assert result.text == text
    assert result.applied_mutations == ()


def test_stage5_preprocessor_is_idempotent() -> None:
    first = preprocess_stage5("국물과 같이 먹는 음식입니다.")
    second = preprocess_stage5(first.text, snapshot=first.snapshot)

    assert first.text == "궁물과 가치 멍는 음식입니다."
    assert second.text == first.text
    assert second.applied_mutations == ()


def test_stage5_preprocessor_accepts_compound_particle_boundaries() -> None:
    result = preprocess_stage5("학교보다 국물에서는 인기가 높습니다.")
    assert result.text == "학꾜보다 궁물에서는 인끼가 높습니다."


def test_stage5_work_plan_contains_only_unresolved_context_choices() -> None:
    result = preprocess_stage5("인기는 높고 노동의 대가는 컸던 기자입니다.")
    payload = json.loads(result.work_plan.to_prompt_json())

    assert result.text.startswith("인끼는")
    kinds = {candidate["kind"] for candidate in payload["candidates"]}
    assert "contextual_standard_pronunciation" in kinds
    assert "natural_speech_contraction" in kinds
    daega = next(
        candidate
        for candidate in payload["candidates"]
        if candidate["surface"] == "대가"
    )
    assert daega["options"] == ["대까"]
    assert "거장" in daega["guidance"]


def test_stage5_work_plan_excludes_candidates_in_protected_surface() -> None:
    text = "https://example.com/대가/file"
    assert build_stage5_work_plan(text).candidates == ()


def test_stage5_work_plan_slices_and_rebases_paragraph_candidates() -> None:
    plan = Stage5WorkPlan(
        (
            Stage5Candidate("S5-0001", 1, 3, "context", "대가", ("대까",), "첫째"),
            Stage5Candidate("S5-0002", 8, 10, "context", "대가", ("대까",), "둘째"),
        )
    )

    sliced = plan.for_span(7, 12)

    assert len(sliced.candidates) == 1
    assert sliced.candidates[0].candidate_id == "S5-0002"
    assert (sliced.candidates[0].start, sliced.candidates[0].end) == (1, 3)
    assert sliced.to_allowed_mutations()[0].source_text == "대가"
