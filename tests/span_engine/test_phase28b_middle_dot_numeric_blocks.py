from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12·3", "일이·삼"),
        ("7·25", "칠·이오"),
        ("10·5", "일영·오"),
        ("1·2·3", "일·이·삼"),
        ("123·456", "일이삼·사오육"),
        ("12·3수치", "일이·삼수치"),
        ("7·25자료", "칠·이오자료"),
        ("1·2·3형", "일·이·삼형"),
        ("12·3-수치", "일이·삼-수치"),
    ],
)
def test_middle_dot_numeric_block_fallback_canonical(text: str, expected: str) -> None:
    # Phase 28B: This is expected to FAIL until implementation in Phase 28C
    assert transform(text) == expected


def test_middle_dot_numeric_block_trace() -> None:
    from engine.span_engine import transform_with_trace
    output = transform_with_trace("12·3")
    # Expected owner: middle_dot_numeric (or similar)
    assert any(claim.owner in {"middle_dot_numeric", "middle_dot_block"} for claim in output.trace.claim_logs)
