from __future__ import annotations

import pytest

from engine.main import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("제1 회", "제-일회"),
        ("제 1 회", "제-일회"),
        ("제1회", "제-일회"),
        ("제1 번", "제-일번"),
        ("제3 문항", "제-삼문항"),
        ("제1", "제-일"),
        ("제2.5", "제-이쩜오"),
        ("제3 조", "제-삼 조"),
    ],
)
def test_prefixed_je_registered_suffix_spacing_is_canonical(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_prefixed_je_latin_unit_contract_is_unchanged() -> None:
    assert transform("제10kg") == "제십-킬로그램"
