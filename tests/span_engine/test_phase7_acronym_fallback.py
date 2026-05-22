from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ABC", "에이비씨"),
        ("XYZ", "엑스와이지"),
        ("NLP", "엔엘피"),
        ("AB는", "에이비는"),
    ],
)
def test_safe_uppercase_acronym_fallback(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["A", "OpenAI", "USB3", "mL", "km", "AI3", "abc"])
def test_acronym_fallback_preserves_unsafe_tokens(text: str) -> None:
    assert transform(text) == text


def test_two_block_hyphen_code_handles_single_letter_prefix() -> None:
    assert transform("A-1") == "에이 원"


def test_dictionary_owner_wins_before_acronym_fallback() -> None:
    output = transform_with_trace("JSON")

    assert output.normalized_text == "제이슨"
    assert any(claim.owner == "dictionary" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "acronym_fallback" for claim in output.trace.claim_logs)
