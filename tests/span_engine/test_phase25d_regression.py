from __future__ import annotations

from engine.main import transform_with_rollout
from engine.span_engine.production_adapter import transform_for_production


def test_phase25d_regression_source_rollout_helpers_remain_stable() -> None:
    assert transform_with_rollout("90km/h", mode="span_default") == "시속 구십 킬로미터"
    assert transform_for_production("90km/h") == "시속 구십 킬로미터"

