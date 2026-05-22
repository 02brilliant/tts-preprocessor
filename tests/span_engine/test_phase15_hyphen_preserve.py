from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "123-4567",
        "12-3456",
        "12345-6789",
        "1234-567",
        "1-2",
        "12-34",
        "123-456",
        "2025-01",
        "1 -2-3",
        "1- 2-3",
        "A-1-2",
        "123-456-7890abc",
        "abc123-456-7890",
        "123-456-7890kg",
        "123--456",
        "-123-456",
        "123-456-",
        "123_456_7890",
        "123/456/7890",
    ],
)
def test_hyphen_preserve_cases(text: str) -> None:
    assert transform(text) == text


def test_spaced_hyphen_numeric_multiblock_policy_v102() -> None:
    assert transform("1 - 2 - 3") == "일 이 삼"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A-1", "에이 원"),
        ("ABC-12", "ABC-12"),
        ("D-14", "디 십사"),
    ],
)
def test_two_block_alpha_numeric_hyphen_policy(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("1-2", "일 이"),
        ("A-1", "에이-일"),
        ("D-14", "디-십사"),
        ("12-3장", "일이 삼장"),
        ("123-456-7890abc", "일이삼 사오육 칠팔구공abc"),
    ],
)
def test_hyphen_forbidden_signatures(text: str, forbidden: str) -> None:
    assert transform(text) != forbidden
