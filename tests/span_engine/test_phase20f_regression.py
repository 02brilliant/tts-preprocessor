from __future__ import annotations

from engine.main import transform
from engine.span_engine.production_adapter import transform_for_production


def test_phase20f_regression_engine_main_remains_stable() -> None:
    assert transform("90km/h") == "시속 구십 킬로미터"


def test_phase20f_regression_span_adapter_output_remains_stable() -> None:
    assert transform_for_production("그리고 우리는 결과를 확인했다") == "그리고, 우리는 결과를 확인했다"
