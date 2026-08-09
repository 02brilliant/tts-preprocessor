from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5·18 민주화운동", "오일팔 민주화운동"),
        ("5·18 민주화 운동", "오일팔 민주화 운동"),
        ("4·19 혁명", "사일구 혁명"),
        ("6·25 전쟁", "육이오 전쟁"),
        ("3·1 운동", "삼일 운동"),
        ("5·18민주화운동", "오일팔민주화운동"),
    ],
)
def test_middle_dot_event_with_keyword(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_bare_middle_dot_event_normalizes_as_fallback() -> None:
    output = transform_with_trace("5·18")

    # Phase 28B: Expected to fail until Phase 28C
    assert output.normalized_text == "오·일팔"
    assert not any(claim.owner == "event" for claim in output.trace.claim_logs)
    # It should be claimed by middle-dot numeric owner (to be implemented)
