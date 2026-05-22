from __future__ import annotations

from engine.main import transform_with_rollout
from engine.span_engine.production_adapter import transform_for_production


def test_phase20f_regression_engine_main_rollout_bridge_remains_stable() -> None:
    assert transform_with_rollout("90km/h", mode="span_default") == "시속 구십 킬로미터"
    assert transform_with_rollout(
        "90km/h",
        mode="span_shadow_compare",
        legacy_transform=lambda text: text,
    ) == "90km/h"
    assert transform_with_rollout(
        "90km/h",
        legacy_transform=lambda text: "LEGACY:" + text,
    ) == "LEGACY:90km/h"


def test_phase20f_regression_span_adapter_output_remains_stable() -> None:
    assert transform_for_production("그리고 우리는 결과를 확인했다") == "그리고, 우리는 결과를 확인했다"
