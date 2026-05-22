from __future__ import annotations

from engine.span_engine import transform


def test_phase18a_regression_smoke() -> None:
    assert transform("15.2km/L") == "리터당 십오쩜이 킬로미터"
    assert transform("3000rpm") == "삼천 알피엠"
    assert transform("역삼동 12번지") == "역삼동 십이번지"
    assert transform("+3°") == "플러스 삼도"
    assert transform("5·18 민주화운동") == "오일팔 민주화운동"
    assert transform("화재가 나면 119에 신고") == "화재가 나면 일일구에 신고"
