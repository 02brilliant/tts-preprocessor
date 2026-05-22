from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[€50]", "€50"),
        ("[50kg]", "50kg"),
        ("[45㎡]", "45㎡"),
        ("가격은 [€50]입니다", "가격은 €50입니다"),
        ("무게는 [50kg]입니다", "무게는 50kg입니다"),
    ],
)
def test_bracket_protection_blocks_unit_currency_claims(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)

    assert transform(text) == expected
    assert not any(
        claim.owner in {"currency", "simple_unit", "special_unit", "number"}
        and claim.span.start >= text.index("[")
        and claim.span.end <= text.rindex("]") + 1
        for claim in output.trace.claim_logs
    )
