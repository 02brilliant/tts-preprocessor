from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "2025.1.3",
        "2025-1-3",
        "25-01-03",
        "2025-01",
        "2025/01",
        "2025-01-03abc",
        "2025-01-03kg",
        "2025-01-03~2025-01-05",
    ],
)
def test_unsupported_dates_preserve(text: str) -> None:
    assert transform(text) == text


def test_spaced_hyphen_date_like_numeric_blocks_use_policy_v102() -> None:
    assert transform("2025 - 01 - 03") == "이천이십오 - 공일 - 공삼"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2025-13-01", "이공이오 일삼 공일"),
        ("2025-00-01", "이공이오 공공 공일"),
        ("2025-01-00", "이공이오 공일 공공"),
        ("2025-02-30", "이공이오 공이 삼공"),
        ("2025/13/01", "이공이오 일삼 공일"),
        ("2025/01/00", "이공이오 공일 공공"),
    ],
)
def test_calendar_invalid_full_dates_use_code_separator_fallback(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("2025-1-3", "이천이십오년 일월 삼일"),
        ("2025-13-01", "이천이십오년 십삼월 일일"),
        ("12.12 사태", "십이월 십이일 사태"),
        ("2025-01-03abc", "이천이십오년 일월 삼일abc"),
    ],
)
def test_unsupported_date_forbidden_signatures_do_not_appear(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden
