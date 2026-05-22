from __future__ import annotations

from engine.span_engine import transform


def test_phase19c_regression_smoke() -> None:
    assert transform("그리고 우리는 결과를 확인했다") == "그리고, 우리는 결과를 확인했다"
    assert transform("90km/h") == "시속 구십 킬로미터"
    assert transform("60fps") == "육십 에프피에스"
    assert transform("종로3가") == "종로삼가"
    assert transform("3만") == "삼만"
    assert transform("ㄱㄴㄷ") == "기역 니은 디귿"
    assert transform("-2.5℃") == "영하 이쩜오도"
    assert transform("123-456-7890") == "일이삼 사오육 칠팔구공"
    assert transform("2025-01-03") == "이천이십오년 일월 삼일"
    assert transform("3~8cm") == "삼에서 팔 센티미터"
    assert transform("€50을 냈다") == "오십 유로를 냈다"
    assert transform("21명") == "스물한 명"
    assert transform("12.12 사태") == "십이십이 사태"
    assert transform("긴급번호 112는") == "긴급번호 일일이는"
