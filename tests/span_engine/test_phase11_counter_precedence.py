from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("50kg", "오십-킬로그램", "simple_unit"),
        ("3킬로그램", "삼-킬로그램", "counter_noun"),
        ("21원", "이십일-원", "currency"),
        ("₩21", "이십일-원", "currency"),
        ("$21", "이십일-달러", "currency"),
    ],
)
def test_counter_precedence_with_unit_currency(
    text: str, expected: str, owner: str
) -> None:
    output = transform_with_trace(text)

    assert transform(text) == expected
    assert any(claim.owner == owner for claim in output.trace.claim_logs)
    if owner != "counter_noun":
        assert not any(claim.owner == "counter_noun" for claim in output.trace.claim_logs)
