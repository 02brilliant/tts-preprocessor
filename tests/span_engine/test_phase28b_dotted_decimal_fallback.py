from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.3", "십이쩜삼"),
        ("7.25", "칠쩜이오"),
        ("10.5", "십쩜오"),
        ("3.14", "삼쩜일사"),
        ("12.03", "십이쩜영삼"),
        ("0.125", "영쩜일이오"),
        ("12.3수치", "십이쩜삼수치"),
        ("3.14값", "삼쩜일사값"),
        ("0.125비율", "영쩜일이오비율"),
        ("7.25자료", "칠쩜이오자료"),
        ("12.3-수치", "십이쩜삼-수치"),
    ],
)
def test_dotted_decimal_fallback_canonical(text: str, expected: str) -> None:
    # Phase 28B: This is expected to FAIL until implementation in Phase 28C
    assert transform(text) == expected


def test_dotted_decimal_fallback_trace() -> None:
    from engine.span_engine import transform_with_trace
    output = transform_with_trace("12.3")
    # Expected owner: decimal (or dotted_decimal_numeric)
    assert any(claim.owner in {"decimal", "dotted_decimal_numeric"} for claim in output.trace.claim_logs)
