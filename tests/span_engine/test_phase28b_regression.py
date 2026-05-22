from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.3-수치", "십이쩜삼-수치"),  # Not an event
        ("12·3-수치", "십이 삼-수치"),    # Not an event
        ("12.3 은 비상계엄", "십이쩜삼 은 비상계엄"),  # Separated by josa
        ("12·3 은 비상계엄", "십이 삼 은 비상계엄"),    # Separated by josa
    ],
)
def test_regression_and_safety_cases(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_bracket_internal_non_reentry() -> None:
    # Bracket content should be protected, no internal owners should claim
    text = "[12.3 비상계엄]"
    output = transform_with_trace(text)
    
    assert output.normalized_text == "12.3 비상계엄"
    assert not any(claim.owner == "event" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "decimal" for claim in output.trace.claim_logs)
