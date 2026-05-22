from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2025-01-03은 휴일", "이천이십오년 일월 삼일은 휴일"),
        ("2025-01-03는 휴일", "이천이십오년 일월 삼일은 휴일"),
        ("시각 13:05를 선택", "시각 십삼시 오분을 선택"),
        ("시각 13:05을 선택", "시각 십삼시 오분을 선택"),
    ],
)
def test_safe_particle_after_generated_date_time(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3월를 선택", "삼월를 선택"),
        ("3월을 선택", "삼월을 선택"),
    ],
)
def test_original_korean_marker_blocks_broad_particle_correction(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
