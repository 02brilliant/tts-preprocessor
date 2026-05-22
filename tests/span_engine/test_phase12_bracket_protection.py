from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[3~8cm]", "3~8cm"),
        ("범위는 [3~8cm]입니다", "범위는 3~8cm입니다"),
        ("(3~8cm)", ""),
        ("범위는 (3~8cm)입니다", "범위는 입니다"),
    ],
)
def test_bracket_protection_with_range(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_bracket_internal_range_claim_is_skipped() -> None:
    output = transform_with_trace("범위는 [3~8cm]입니다")

    assert output.normalized_text == "범위는 3~8cm입니다"
    assert not any(claim.owner.startswith("range") for claim in output.trace.claim_logs)
    assert output.trace.bracket_filter_logs
