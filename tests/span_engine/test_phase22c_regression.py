from __future__ import annotations

from engine.main import transform
from engine.span_engine.transform import transform as span_transform


def test_phase22c_span_transform_regression_remains_stable() -> None:
    assert span_transform("[3kg]") == "3kg"
    assert span_transform("21명") == "스물한 명"
    assert span_transform("전문가 유지") == "전문가 유지"
    assert span_transform("http://x/90km/h") == "http://x/90km/h"


def test_phase22c_current_main_transform_regression_is_stable() -> None:
    assert transform("21명") == "스물한 명"
    assert transform("전문가 유지") == "전문가 유지"
    assert transform("http://x/90km/h") == "http://x/90km/h"
