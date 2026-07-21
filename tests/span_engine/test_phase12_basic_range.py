from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3~8", "삼에서 팔"),
        ("1~11", "일에서 십일"),
        ("10~20", "십에서 이십"),
        ("100~120", "백에서 백이십"),
        ("3∼8", "삼에서 팔"),
        ("범위는 3~8이다", "범위는 삼에서 팔이다"),
        ("값은 10~20은 가능", "값은 십에서 이십은 가능"),
    ],
)
def test_basic_numeric_range(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3-8", "3-8"),
        ("1 - 2", "일 빼기 이"),
    ],
)
def test_hyphen_and_spaced_basic_subtraction(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_spaced_tilde_range_transforms_policy_update() -> None:
    assert transform("3 ~ 8") == "삼에서 팔"


def test_phase13_date_owner_updates_former_hyphen_range_preserve_case() -> None:
    assert transform("2025-01-03") == "이천이십오년 일월 삼일"
