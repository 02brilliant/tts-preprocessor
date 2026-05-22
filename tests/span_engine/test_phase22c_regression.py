from __future__ import annotations

from engine.main import transform
from engine.span_engine.transform import transform as span_transform
from engine.span_engine.compare import classify_compare_result


def test_phase22c_span_transform_regression_remains_stable() -> None:
    assert span_transform("[3kg]") == "3kg"
    assert span_transform("21명") == "스물한 명"
    assert span_transform("전문가 유지") == "전문가 유지"
    assert span_transform("http://x/90km/h") == "http://x/90km/h"


def test_phase22c_actual_legacy_transform_regression_is_not_rewritten() -> None:
    assert transform("21명") == "스물한 명"
    assert transform("전문가 유지") == "전문가 유지"
    assert transform("http://x/90km/h") == "http://x/90km/h"


def test_phase22c_actual_legacy_compare_for_policy_inputs_remains_classified() -> None:
    for input_text in ("FTA은", "종로3가"):
        result = classify_compare_result(
            input_text=input_text,
            legacy_output=transform(input_text),
            span_output=span_transform(input_text),
        )
        assert result.category in {"same", "intended_v5_change"}
