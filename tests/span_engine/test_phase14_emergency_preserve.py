from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("112", "백십이"),
        ("119", "백십구"),
        ("112는 일반 번호", "백십이는 일반 번호"),
        ("119에", "백십구에"),
        ("112명", "백십이-명"),
        ("119건", "백십구-건"),
        ("112번", "백십이-번"),
        ("119호", "백십구-호"),
        ("1199", "천백구십구"),
    ],
)
def test_emergency_missing_context_or_disallowed_tail_uses_expected_fallback(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert not any(claim.owner == "emergency" for claim in output.trace.claim_logs)


@pytest.mark.parametrize("text", ["112abc", "a112", "0119"])
def test_emergency_alpha_contamination_or_leading_zero_preserves(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("112", "일일이"),
        ("112명", "일일이명"),
        ("119건", "일일구건"),
        ("119에", "일일구에"),
        ("112번", "일일이번"),
    ],
)
def test_forbidden_emergency_signatures(text: str, forbidden: str) -> None:
    assert transform(text) != forbidden
