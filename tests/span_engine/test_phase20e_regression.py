from __future__ import annotations

from engine.main import transform as facade_transform
from engine.span_engine import transform
from engine.span_engine.production_adapter import transform_for_production


def test_phase20e_regression_span_adapter_outputs_remain_stable() -> None:
    assert transform_for_production("90km/h") == "시속 구십 킬로미터"
    assert transform_for_production("그리고 우리는 결과를 확인했다") == "그리고, 우리는 결과를 확인했다"


def test_phase20e_regression_canonical_facade_remains_stable() -> None:
    assert facade_transform("90km/h") == "시속 구십 킬로미터"


def test_phase20e_regression_span_transform_outputs_remain_stable() -> None:
    assert transform("90km/h") == "시속 구십 킬로미터"
    assert transform("그리고 우리는 결과를 확인했다") == "그리고, 우리는 결과를 확인했다"
