from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def test_phase18a_current_normalized_output_contract() -> None:
    assert transform("90km/h") == "시속 구십 킬로미터"
    assert transform("60fps") == "육십 에프피에스"
    assert transform("종로3가") == "종로 삼 가"
    assert transform("3만") == "삼만"
    assert transform("ㄱㄴㄷ") == "기역 니은 디귿"
    assert transform("-2.5℃") == "영하 이쩜오도"
    assert transform("123-456-7890") == "일이삼 사오육 칠팔구공"
    assert transform("2025-01-03") == "이천이십오년 일월 삼일"
    assert transform("3~8cm") == "삼에서 팔 센티미터"
    assert transform("€50을 냈다") == "오십 유로를 냈다"
    assert transform("21명") == "스물한 명"
    assert transform("12.12 사태") == "십이십이 사태"
    assert transform("긴급번호 112는") == "긴급번호 일일이는"


def test_phase18a_trace_contract_allows_empty_prosody_logs() -> None:
    output = transform_with_trace("오늘 우리는 새로운 시스템을 테스트하고 결과를 확인합니다")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert hasattr(output.trace, "claim_logs")
    assert hasattr(output.trace, "parser_logs")
    assert hasattr(output.trace, "render_logs")
    assert hasattr(output.trace, "validation_logs")
    assert hasattr(output.trace, "bracket_filter_logs")
    assert not getattr(output.trace, "prosody_logs", [])


def test_phase18b_policy_example_leading_connector_comma_contract() -> None:
    assert (
        transform("그리고 12.12 사태 자료와 €1,234.56 보고서를 검토한다")
        == "그리고, 십이십이 사태 자료와 천이백삼십사쩜오육 유로 보고서를 검토한다"
    )
