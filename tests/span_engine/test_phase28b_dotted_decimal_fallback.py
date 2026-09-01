from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('12.3', '십이-쩜-삼'),
        ('7.25', '칠-쩜-이오'),
        ('10.5', '십-쩜-오'),
        ('3.14', '삼-쩜-일사'),
        ('12.03', '십이-쩜-영삼'),
        ('0.125', '영-쩜-일이오'),
        ('12.3수치', '십이-쩜-삼수치'),
        ('3.14값', '삼-쩜-일사값'),
        ('0.125비율', '영-쩜-일이오비율'),
        ('7.25자료', '칠-쩜-이오자료'),
        ('12.3-수치', '십이-쩜-삼-수치'),
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
