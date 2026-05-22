from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("$100", "백 달러", "currency"),
        ("50kg", "오십 킬로그램", "simple_unit"),
        ("45㎡", "사십오 제곱미터", "special_unit"),
        ("100MB", "백 메가바이트", "simple_unit"),
    ],
)
def test_unit_currency_precede_general_number(
    text: str, expected: str, owner: str
) -> None:
    output = transform_with_trace(text)

    assert transform(text) == expected
    assert any(claim.owner == owner for claim in output.trace.claim_logs)
    assert not any(claim.owner == "number" for claim in output.trace.claim_logs)
