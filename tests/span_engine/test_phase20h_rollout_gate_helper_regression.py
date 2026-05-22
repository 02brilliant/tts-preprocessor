from __future__ import annotations

from engine.main import transform_with_rollout
from engine.span_engine.production_adapter import transform_for_production


def test_phase20h_rollout_gate_helper_regression_existing_rollout_outputs_remain_stable() -> None:
    assert transform_with_rollout("90km/h", mode="span_default") == "시속 구십 킬로미터"
    assert transform_with_rollout(
        "90km/h",
        mode="span_shadow_compare",
        legacy_transform=lambda text: text,
    ) == "90km/h"
    assert transform_for_production("90km/h") == "시속 구십 킬로미터"
