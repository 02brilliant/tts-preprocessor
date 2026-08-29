from __future__ import annotations

from engine.span_engine.transform import transform

def test_phase21c_transform_regression_remains_stable() -> None:
    assert transform("[3kg]") == "3kg"
    assert transform("21명") == "스물한-명"
    assert transform("전문가 유지") == "전문가 유지"
    assert transform("http://x/90km/h") == "http://x/90km/h"
