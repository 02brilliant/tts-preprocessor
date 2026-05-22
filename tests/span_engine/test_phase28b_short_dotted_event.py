from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.3 비상계엄", "십이삼 비상계엄"),
        ("12·3 비상계엄", "십이삼 비상계엄"),
        ("12.3-비상계엄", "십이쩜삼-비상계엄"),
        ("12·3-비상계엄", "십이 삼-비상계엄"),
        ("4.19 혁명", "사일구 혁명"),
        ("4·19 혁명", "사일구 혁명"),
        ("5.18 민주화 운동", "오일팔 민주화 운동"),
        ("5·18 민주화 운동", "오일팔 민주화 운동"),
        ("6.27 부동산대책", "육이칠 부동산대책"),
        ("6·27 부동산대책", "육이칠 부동산대책"),
        ("12.12 사태", "십이십이 사태"),
        ("12·12 사태", "십이십이 사태"),
    ],
)
def test_short_dotted_middle_dot_event_canonical(text: str, expected: str) -> None:
    # Phase 28B: This is expected to FAIL until implementation in Phase 28C
    assert transform(text) == expected


def test_short_dotted_event_trace() -> None:
    output = transform_with_trace("12.3 비상계엄")
    # Expected owner: event
    assert any(claim.owner == "event" for claim in output.trace.claim_logs)
    assert any(piece.owner == "event" and piece.provenance == "GENERATED_READING" for piece in output.render_pieces)
