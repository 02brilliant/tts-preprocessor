from __future__ import annotations

from engine.span_engine import transform


def test_phase15_regression_smoke() -> None:
    assert transform("AI") == "에이아이"
    assert transform("FTA은 적용됐다") == "에프티에이는 적용됐다"
    assert transform("가격은 [3kg]입니다") == "가격은 3kg입니다"
    assert transform("€50을 냈다") == "오십 유로를 냈다"
    assert transform("21명") == "스물한 명"
    assert transform("3~8cm") == "삼에서 팔 센티미터"
    assert transform("2025-01-03") == "이천이십오년 일월 삼일"
    assert transform("12.12 사태") == "십이십이 사태"
    assert transform("긴급번호 112는") == "긴급번호 일일이는"

