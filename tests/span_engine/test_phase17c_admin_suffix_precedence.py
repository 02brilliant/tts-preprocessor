from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def test_phase17c_admin_suffix_precedence_smoke() -> None:
    assert transform("종로3가") == "종로 삼 가"
    assert transform("역삼동 12번지") == "역삼동 십이 번지"
    assert transform("3시") == "세 시"
    assert transform("21명") == "스물한 명"
    assert transform("21호") == "21호"
    assert transform("101동") == "백일 동"
    assert transform("1~3층") == "일에서 삼 층"
    assert transform("2025-01-03") == "이천이십오년 일월 삼일"


def test_phase17c_admin_suffix_owner_trace() -> None:
    output = transform_with_trace("종로3가")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "administrative_suffix" for claim in output.trace.claim_logs)


def test_phase17c_admin_suffix_conflict_trace_keeps_existing_owner() -> None:
    output = transform_with_trace("21호")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert [claim.owner for claim in output.trace.claim_logs] == [
        "contextual_number_unit"
    ]
