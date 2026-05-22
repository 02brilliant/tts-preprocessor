from __future__ import annotations

import importlib


def test_phase20c_rollout_adapter_regression_smoke() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    transform_for_production = getattr(adapter, "transform_for_production")

    assert transform_for_production("90km/h") == "시속 구십 킬로미터"
    assert transform_for_production("60fps") == "육십 에프피에스"
    assert transform_for_production("종로3가") == "종로삼가"
    assert transform_for_production("3만") == "삼만"
    assert transform_for_production("ㄱㄴㄷ") == "기역 니은 디귿"
    assert transform_for_production("-2.5℃") == "영하 이쩜오도"
    assert transform_for_production("123-456-7890") == "일이삼 사오육 칠팔구공"
    assert transform_for_production("2025-01-03") == "이천이십오년 일월 삼일"
    assert transform_for_production("3~8cm") == "삼에서 팔 센티미터"
    assert transform_for_production("€50을 냈다") == "오십 유로를 냈다"
    assert transform_for_production("21명") == "스물한 명"
    assert transform_for_production("12.12 사태") == "십이십이 사태"
    assert transform_for_production("긴급번호 112는") == "긴급번호 일일이는"
    assert transform_for_production("그리고 우리는 결과를 확인했다") == "그리고, 우리는 결과를 확인했다"
