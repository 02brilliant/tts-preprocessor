from __future__ import annotations

from engine.span_engine import transform
from engine.span_engine.production_adapter import transform_for_production


def test_phase20c_shadow_mode_regression_smoke() -> None:
    assert transform_for_production("90km/h") == "시속 구십 킬로미터"
    assert transform_for_production("60fps") == "육십 에프피에스"
    assert transform_for_production("종로3가") == "종로삼가"
    assert transform_for_production("그리고 우리는 결과를 확인했다") == "그리고, 우리는 결과를 확인했다"

    assert transform("90km/h") == "시속 구십 킬로미터"
    assert transform("그리고 우리는 결과를 확인했다") == "그리고, 우리는 결과를 확인했다"
