from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def test_large_unit_atomic_precedence_regression_smoke() -> None:
    assert transform("3만") == "삼만"
    assert transform("123") == "백이십삼"
    assert transform("21명") == "스물한-명"
    assert transform("3~8cm") == "삼에서 팔-센티미터"
    assert transform("2025-01-03") == "이천이십오년 일월 삼일"
    assert transform("123-456-7890") == "일이삼 사오육 칠팔구공"


def test_large_unit_atomic_trace_owner() -> None:
    output = transform_with_trace("3만")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "large_unit_atomic" for claim in output.trace.claim_logs)


def test_number_owner_stays_number_without_large_unit() -> None:
    output = transform_with_trace("123")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "number" for claim in output.trace.claim_logs)
