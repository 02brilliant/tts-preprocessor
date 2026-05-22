from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3~8을 선택", "삼에서 팔을 선택"),
        ("3~8를 선택", "삼에서 팔을 선택"),
        ("3~5를 선택", "삼에서 오를 선택"),
        ("3~5을 선택", "삼에서 오를 선택"),
        ("3~8cm을 측정", "삼에서 팔 센티미터를 측정"),
        ("3~8cm를 측정", "삼에서 팔 센티미터를 측정"),
    ],
)
def test_safe_particle_exception_after_generated_range(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1~11월을 선택", "일월에서 십일월을 선택"),
        ("1~11월를 선택", "일월에서 십일월를 선택"),
    ],
)
def test_korean_suffix_between_range_and_particle_blocks_broad_correction(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
