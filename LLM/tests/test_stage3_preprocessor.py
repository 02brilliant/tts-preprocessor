from __future__ import annotations

import json

import pytest

from LLM import stage_engine
from LLM.client import GenerationResult
from LLM.invocation_gate import decide_llm_invocation
from LLM.provenance import build_normalization_snapshot
from LLM.selection_pipeline import build_selection_plan, render_selection_response, parse_selection_response, SelectionResponseError
from LLM.stage3_preprocessor import preprocess_stage3
from LLM.stage4_preprocessor import preprocess_stage4
from LLM.stage5_preprocessor import preprocess_stage5
from LLM.response_validation import validate_speech_text
from engine.main import transform_output


@pytest.mark.parametrize(("source", "expected"), [
    ("회의는 09:30에 시작합니다.", "회의는 아홉시 삼십분에 시작합니다."),
    ("금리는 0.5%p 올랐습니다.", "금리는 영-쩜-오-퍼센트포인트 올랐습니다."),
    ("무게는 3kg입니다.", "무게는 삼-킬로그램입니다."),
    ("가격은 USD 10입니다.", "가격은 십-달러입니다."),
    ("기간은 2026-09-07부터입니다.", "기간은 이천이십육년 구월 칠일부터입니다."),
])
def test_certified_readings_are_applied_without_model_and_locked(source, expected):
    prepared = preprocess_stage3(source)
    assert prepared.text == expected
    assert any(s.provenance == "GENERATED_RESIDUAL_READING" and s.locked for s in prepared.snapshot.spans)
    assert not decide_llm_invocation(prepared.text, stage_level=3, selection_plan=prepared.work_plan).call_llm
    assert preprocess_stage3(prepared.text, snapshot=prepared.snapshot).text == expected


@pytest.mark.parametrize("source", [
    "코드는 007입니다.", "버전은 v1.2.3입니다.", "모델은 AB-12-X입니다.",
    "파일 report_v2.json입니다.", "https://example.com/3kg?q=3번", "mail123@example.com",
    '`3kg 3번 XQZ`', '{"value":"3kg", "n":3}',
    "This is a protected English sentence with 3kg and XQZ.",
    "KBS news", "제품은 UnregisteredName입니다.",
    "코드는 00.5입니다.", "표기는 1.2.3입니다.",
])
def test_protected_unknown_and_malformed_surfaces_are_preserved(source):
    prepared = preprocess_stage3(source)
    assert prepared.text == source
    assert not [c for c in prepared.work_plan.candidates if c.kind.startswith("residual_") or c.kind == "deferred_n_beon"]


def test_duplicate_numbers_are_selected_by_exact_occurrence():
    source = "3번 맡았다. 3번 받았다."
    plan = build_selection_plan(source, stage=3)
    choices = [c for c in plan.candidates if c.kind == "deferred_n_beon"]
    assert len(choices) == 2
    response = json.dumps({"schema_version": 1, "decisions": [
        {"id": choices[1].candidate_id, "option": 0},
        {"id": choices[0].candidate_id, "option": 1},
    ]})
    output = render_selection_response(source, plan=plan, response_text=response)
    assert output == "세-번 맡았다. 삼번 받았다."
    assert validate_speech_text(source, output, stage=3, candidates=plan.to_allowed_mutations()).ok


@pytest.mark.parametrize(("source", "expected"), [
    ("3번 처리했습니다.", "세-번 처리했습니다."),
    ("3번 항목을 처리했습니다.", "삼번 항목을 처리했습니다."),
    ("3번을 처리했습니다.", "삼번을 처리했습니다."),
])
def test_high_confidence_beon_context_is_code_rendered_and_locked(source, expected):
    prepared = preprocess_stage3(source)
    assert prepared.text == expected
    assert not any(c.kind == "deferred_n_beon" for c in prepared.work_plan.candidates)
    assert any(
        span.provenance == "GENERATED_RESIDUAL_READING" and span.locked
        for span in prepared.snapshot.spans
    )


@pytest.mark.parametrize("unit", ["분", "대", "부", "동", "판", "척", "장", "권", "편", "점", "조"])
def test_contextual_counter_options_and_preservation(unit):
    source = f"3{unit}을 확인했다."
    plan = build_selection_plan(source, stage=3)
    candidate = next(c for c in plan.candidates if c.kind == "residual_counter")
    assert candidate.options == (f"삼{unit}", f"세-{unit}")
    assert not candidate.required
    assert render_selection_response(source, plan=plan, response_text='{"schema_version":1,"decisions":[]}') == source


@pytest.mark.parametrize(("source", "kind", "reading"), [
    ("표현은 3/4 입니다.", "residual_fraction", "사분의 삼"),
    ("표현은 3:4 입니다.", "residual_ratio_or_time", "삼 대 사"),
])
def test_numeric_punctuation_is_consumed_only_by_approved_whole_candidate(source, kind, reading):
    plan = build_selection_plan(source, stage=3)
    candidate = next(c for c in plan.candidates if c.kind == kind)
    response = json.dumps({"schema_version": 1, "decisions": [{"id": candidate.candidate_id, "option": 0}]})
    output = render_selection_response(source, plan=plan, response_text=response)
    assert reading in output
    assert validate_speech_text(source, output, stage=3, candidates=plan.to_allowed_mutations()).ok


def test_stage3_never_offers_korean_pronunciation_or_contraction():
    plan = build_selection_plan("기자입니다. 국물과 색연필입니다. 산업용지역전기요금제입니다.", stage=3)
    assert any(c.kind == "compound_boundary" for c in plan.candidates)
    assert not any("contraction" in c.kind or "pronunciation" in c.kind for c in plan.candidates)


def test_stage3_prosody_candidates_only_follow_safe_clause_endings():
    source = "장비 엑스큐지를 점검했지만 담당자는 결과를 다시 확인했습니다."
    plan = build_selection_plan(source, stage=3)
    commas = [c for c in plan.candidates if c.kind == "prosody_comma"]
    assert [source[:c.start].split()[-1] for c in commas] == ["점검했지만"]


def test_stage_hierarchy_inherits_all_base_choices():
    source = "3번 확인했고 새 장비 XQZ를 다시 점검했습니다."
    signatures = [{(c.start, c.end, c.kind, c.options) for c in build_selection_plan(source, stage=stage).candidates} for stage in (3, 4, 5)]
    assert signatures[0] <= signatures[1] <= signatures[2]


@pytest.mark.parametrize("prepare", [preprocess_stage3, preprocess_stage4, preprocess_stage5])
def test_existing_engine_locks_survive_shared_residual_preprocessing(prepare):
    output = transform_output("3번 버스와 3kg입니다.")
    snapshot = build_normalization_snapshot(output)
    prepared = prepare(output.normalized_text, snapshot=snapshot)
    for span in snapshot.spans:
        if span.locked:
            assert span.text in prepared.text
    assert all(prepared.text[s.normalized_start:s.normalized_end] == s.text for s in prepared.snapshot.spans)


def test_explicit_plan_closes_legacy_regex_escape_hatch():
    source = "새 장비 XQZ입니다."
    plan = build_selection_plan(source, stage=3)
    result = validate_speech_text(source, "새 장비 임의발음입니다.", stage=3, candidates=plan.to_allowed_mutations())
    assert not result.ok


@pytest.mark.parametrize("response", [
    '{"schema_version":1.0,"decisions":[]}',
    '{"schema_version":true,"decisions":[]}',
    '{"schema_version":1,"decisions":[{"id":"S3-0001","option":true}]}',
    '{"schema_version":1,"decisions":[{"id":"S4-0001","option":0}]}',
])
def test_stage3_rejects_invalid_selection_contract(response):
    with pytest.raises(SelectionResponseError):
        parse_selection_response(response, plan=build_selection_plan("3번 확인했다.", stage=3))


def test_invalid_model_response_falls_back_to_prepared_base(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy")
    prepared = preprocess_stage3("무게는 3kg이고 3번 확인했다.")
    monkeypatch.setattr(stage_engine, "generate", lambda **kw: GenerationResult(text="임의 문장", elapsed_ms=1))
    result = stage_engine.transform(prepared.text, model="gemma4:e4b", snapshot=prepared.snapshot, selection_plan=prepared.work_plan)
    assert result.speech_text == prepared.text
    assert "삼-킬로그램" in result.speech_text
    assert result.validation_fallback


def test_unknown_residual_is_diagnostic_not_request_failure(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy")
    monkeypatch.setattr(stage_engine, "generate", lambda **kw: GenerationResult(text='{"schema_version":1,"decisions":[]}', elapsed_ms=1))
    result = stage_engine.transform("제품 UnregisteredName입니다.", model="gemma4:e4b")
    assert result.speech_text == "제품 UnregisteredName입니다."
    assert not result.validation_fallback
    assert result.validation_issues[0].code == "RESIDUAL_SPEECH_SURFACE"
