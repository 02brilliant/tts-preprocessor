from __future__ import annotations

from engine.span_engine import transform


def test_date_precedence_over_hyphen() -> None:
    assert transform("2025-01-03") == "이천이십오년 일월 삼일"
    assert transform("날짜는 2025-01-03입니다") == "날짜는 이천이십오년 일월 삼일입니다"
    assert transform("2025-13-01") == "이공이오 일삼 공일"
    assert transform("2025-01") == "2025-01"
    assert transform("25-01-03") == "25-01-03"
    assert "이공이오 공일 공삼" not in transform("2025-01-03")
    assert "이천이십오년 십삼월 일일" not in transform("2025-13-01")
