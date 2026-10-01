from dataclasses import replace

import pytest

from engine.main import transform, transform_output, transform_simplified
from engine.span_engine.models import ContextualDecisionKind, SourceSpan, Surface, RenderPiece
from engine.span_engine.numeric_plan import make_plan, number_component, vowel_data
from engine.span_engine.numeric_long_vowel import render_numeric_plan, apply_numeric_surface
from LLM.provenance import build_normalization_snapshot
from LLM.selection_pipeline import (
    SelectionDecision, build_selection_plan, compose_selection, selection_numeric_annotations,
)


@pytest.mark.parametrize("source,expected", [
    ("2", "이~"), ("20", "이~십"), ("22", "이~십이"),
    ("202", "이~백이"), ("2002", "이~천이"),
    ("4", "사~"), ("40", "사~십"), ("42", "사~십이"),
    ("5", "오~"), ("50", "오~십"), ("52", "오~십이"),
    ("245", "이~백사십오"), ("520", "오~백이십"),
    ("2개", "두~개"), ("12개", "열~두-개"), ("22개", "스물두-개"),
    ("3명", "세~명"), ("13명", "열~세-명"), ("23명", "스물세-명"),
    ("4마리", "네~마리"), ("14마리", "열~네-마리"), ("24마리", "스물네-마리"),
    ("10개", "열~개"), ("20개", "스무-개"),
    ("10,000", "만"), ("20,000", "이~만"), ("52,025", "오~만 이~천이십오"),
    ("20kg", "이~십-킬로그램"), ("-5℃", "영하 오~도"),
    ("2~5명은", "두~명에서 다섯-명은"), ("5~2개", "다섯-개에서 두~개"),
    ("2~5kg", "이~에서 오~킬로그램"),
    ("2.45", "이~쩜-사오"), ("20.45", "이~십-쩜-사오"),
    ("15.24", "십오-쩜-이사"), ("2.05%", "이~쩜-영오-퍼센트"),
    ("2.50kg", "이~쩜-오영-킬로그램"),
    ("1.23456", "일-쩜-이삼사-오육"), ("1.23456789", "일-쩜-이삼사오-육칠팔구"),
    ("2월", "이~월"), ("4월", "사~월"), ("5월", "오~월"),
    ("6월", "유월"), ("10월", "시월"),
    ("2026년 5월 22일", "이~천이십육년 오~월 이~십이일"),
    ("2026-05-22", "이~천이십육년 오~월 이~십이일"),
    ("2~5월", "이~월에서 오~월"),
    ("2시", "두~시"), ("5시", "다섯시"), ("12시", "열~두시"),
    ("20시", "이~십시"), ("2시 5분", "두~시 오~분"),
    ("2시5분", "두~시 오~분"), ("2~5시", "두~시에서 다섯시"),
    ("12시간", "열~두-시간"), ("2분 동안 기다렸다.", "이~분 동안 기다렸다."),
    ("2초", "이~초"), ("회의는 14:25에 시작한다.", "회의는 십사시 이~십오분에 시작한다."),
    ("2/5", "오~분의 이~"), ("22/25", "이~십오분의 이~십이"),
    ("3/4만큼", "사~분의 삼만큼"),
    ("전체의 3/4만큼 옮겼다.", "전체의 사~분의 삼만큼 옮겼다."),
    ("5분의2", "오~분의이~"), ("5 분의 2", "오~ 분의 이~"),
    ("숫자 4를 선택하세요.", "숫자 사~를 선택하세요."),
    ("5을 더했다", "오~를 더했다"), ("5으로 나누다", "오~로 나누다"),
    ("3~5을 선택", "삼에서 오~를 선택"),
    ("1,200분45초", "천이백분 사~십오초"),
    ("24~48시간 작업", "이~십사-시간에서 사~십팔-시간 작업"),
    ("24:00", "이~십사시"), ("12:00", "열~두시"),
    ("5m/s", "초속 오~ 미터"),
])
def test_approved_common_output(source, expected):
    output = transform_output(source)
    assert output.normalized_text == transform_simplified(source) == expected
    assert "~-" not in expected and "-~" not in expected
    assert not output.trace.fallback_logs
    assert all(log.passed for log in output.trace.validation_logs)
    assert transform(expected) == expected
    for annotation in output.numeric_annotations:
        assert annotation.alignment == "exact"
        assert expected[annotation.output_span.start:annotation.output_span.end] == annotation.plan.text


@pytest.mark.parametrize("source,expected", [
    ("2번", "2번"), ("2호", "2호"), ("2층", "2층"), ("2분", "2분"),
    ("14:25", "14:25"), ("제2차", "제-이차"), ("제2조", "제-이조"),
    ("제2항", "제-이항"), ("2호선", "이-호선"), ("2호실", "이-호실"),
    ("40명", "마흔-명"), ("50명", "쉰-명"),
    ("010-2455-2485", "공일공 이사오오 이사팔오"),
    ("두 개, 이 사람, 사월", "두 개, 이 사람, 사월"),
    ("이~-사람", "이~-사람"), ("`2.45`", "`2.45`"),
    ("https://example.com/3/4만큼", "https://example.com/3/4만큼"),
    ("3/4만큼테스트", "3/4만큼테스트"),
    ("5시 방향", "다섯-시 방향"),
    ("2.5시간", "이-쩜-오-시간"),
    ("제2회", "제-이회"), ("제2편", "제-이편"),
])
def test_exclusions_and_source_preservation(source, expected):
    assert transform(source) == expected


def test_evidence_and_boundaries_describe_actual_output():
    for source in ["2개", "12개", "12시", "2.50kg", "52,025", "2~5명"]:
        output = transform_output(source)
        for annotation in output.numeric_annotations:
            plan = annotation.plan
            for boundary in plan.boundaries:
                if boundary.render_span:
                    assert plan.text[boundary.render_span.start:boundary.render_span.end] == boundary.text
            for component in plan.components:
                assert component.render_span is not None
                for target in component.vowels:
                    assert target.render_span is not None
                    spoken = plan.text[target.render_span.start:target.render_span.end]
                    assert spoken.replace("~", "") == target.lexeme
                    if target.target == "long":
                        assert spoken.startswith(target.lexeme[0] + "~")
                    assert not hasattr(target, "realized")
    assert not any(b.text == "-" for b in transform_output("12시").numeric_annotations[0].plan.boundaries
                   if b.origin == "generated")
    month = transform_output("4월").numeric_annotations[0].plan.components[0].vowels[0]
    assert month.reason == "calendar_month_dictionary" and month.lexeme_id == "krdict:20228"
    assert set(vowel_data()["months"]) == {"2", "4", "5"}


def test_original_time_space_is_not_a_generated_boundary():
    pieces = [
        RenderPiece("세-", "GENERATED_READING", SourceSpan(0, 1), "time"),
        RenderPiece("시", "ORIGINAL_KOREAN", SourceSpan(1, 2)),
        RenderPiece(" ", "ORIGINAL_SPACE", SourceSpan(2, 3)),
        RenderPiece("오", "GENERATED_READING", SourceSpan(3, 4), "time"),
        RenderPiece("분", "ORIGINAL_KOREAN", SourceSpan(4, 5)),
    ]
    text = "".join(p.text for p in pieces)
    surface = Surface("TIME_SURFACE", "time", "3시 5분", SourceSpan(0, 5),
                      text, render_pieces=pieces)
    plan = make_plan("3시 5분", SourceSpan(0, 5), "time", ContextualDecisionKind.CONFIRMED,
                     "clock", "integer", "test", text,
                     (number_component("3", "hour", "native"), number_component("5", "minute")))
    apply_numeric_surface(surface, plan)
    spaces = [b for b in surface.numeric_plan.boundaries if b.render_span and b.text == " "]
    assert len(spaces) == 1 and spaces[0].origin == "original"
    assert spaces[0].source_span == SourceSpan(2, 3)


def test_native_long_marker_does_not_relax_original_particle_guard():
    assert transform("오~을 더했다") == "오~을 더했다"


def test_unknown_and_unmapped_targets_do_not_guess():
    plan = make_plan("2", SourceSpan(0, 1), "number", ContextualDecisionKind.CONFIRMED,
                     "cardinal", "integer", "test", "다른 출력", (number_component("2"),))
    rendered = render_numeric_plan(plan)
    assert rendered.text == "다른 출력" and rendered.marker_status == "component_coordinates_unresolved"
    assert rendered.components[0].vowels[0].render_span is None
    assert render_numeric_plan(replace(plan, decision=ContextualDecisionKind.DEFERRED)).marker_status == "decision_unresolved"
    for source in ["22개", "40명", "010-2455-2485", "15.24"]:
        assert "~" not in transform(source)


@pytest.mark.parametrize("stage", [3, 4])
@pytest.mark.parametrize("source,options", [
    ("2번", ("이~번", "두~번")), ("2호", ("이~호",)), ("2층", ("이~층",)),
])
def test_llm_selects_pre_rendered_options_with_exact_metadata(stage, source, options):
    output = transform_output(source)
    snapshot = build_normalization_snapshot(output)
    plan = build_selection_plan(output.normalized_text, stage=stage, snapshot=snapshot)
    candidate = next(c for c in plan.candidates if c.surface == source)
    assert candidate.options == options
    assert set(candidate.to_payload()) == {"id", "span", "kind", "surface", "options", "required", "guidance", "source"}
    assert compose_selection(source, plan=plan, decisions=()) == source
    for index, expected in enumerate(options):
        decision = SelectionDecision(candidate.candidate_id, index)
        assert compose_selection(source, plan=plan, decisions=(decision,)) == expected
        annotations = selection_numeric_annotations(snapshot, plan=plan, decisions=(decision,))
        assert len(annotations) == 1 and annotations[0].plan.text == expected
        assert annotations[0].output_span == SourceSpan(0, len(expected))
        assert annotations[0].plan.marker_status == "rendered"


def test_repeated_numbers_unit_copy_and_locked_candidates():
    source = "2개와 12시, 2개를 2~5명에게 나눴다."
    output = transform_output(source)
    assert output.normalized_text == "두~개와 열~두시, 두~개를 두~명에서 다섯-명에게 나눴다."
    assert [a.plan.source_span.start for a in output.numeric_annotations] == [0, 4, 9, 13]
    copies = [p for p in output.render_pieces if p.metadata.get("generated_unit_copy")]
    assert len(copies) == 1 and copies[0].text == "명"
    assert any(p.provenance == "ORIGINAL_KOREAN" and p.text == "명에게" for p in output.render_pieces)
    snapshot = build_normalization_snapshot(output)
    for stage in [3, 4]:
        selection = build_selection_plan(output.normalized_text, stage=stage, snapshot=snapshot)
        for candidate in selection.candidates:
            assert all(not (candidate.start < a.output_span.end and a.output_span.start < candidate.end)
                       for a in snapshot.numeric_annotations)


@pytest.mark.parametrize('stage', [3, 4])
def test_llm_ratio_clock_options_share_verified_vowel_renderer(stage):
    output = transform_output('14:25')
    snapshot = build_normalization_snapshot(output)
    selection = build_selection_plan('14:25', stage=stage, snapshot=snapshot)
    candidate = next(c for c in selection.candidates if c.surface == '14:25')
    assert candidate.options == ('십사 대 이~십오', '십사시 이~십오분')
    for index, expected in enumerate(candidate.options):
        decision = SelectionDecision(candidate.candidate_id, index)
        assert compose_selection('14:25', plan=selection, decisions=(decision,)) == expected
        annotation, = selection_numeric_annotations(snapshot, plan=selection, decisions=(decision,))
        assert annotation.plan.marker_status == 'rendered'
        assert annotation.output_span == SourceSpan(0, len(expected))


def test_spoken_zero_minute_and_omitted_clock_minute_have_distinct_coordinates():
    spoken = transform_output("5시0분")
    minute = next(c for a in spoken.numeric_annotations for c in a.plan.components if c.role == "minute")
    assert minute.render_span.end - minute.render_span.start == 1
    assert all(v.reason != "not_spoken_in_owner_reading" for v in minute.vowels)
    omitted = transform_output("12:00").numeric_annotations[0].plan.components[1]
    assert omitted.render_span.start == omitted.render_span.end
    assert all(v.render_span is None and v.reason == "not_spoken_in_owner_reading" for v in omitted.vowels)
