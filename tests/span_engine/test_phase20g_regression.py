from __future__ import annotations

from api.binary_runtime import run_transform_binary_with_rollout
from engine.api_interface import normalize_text_with_rollout
from engine.main import transform_with_rollout
from engine.span_engine.production_adapter import transform_for_production


def test_phase20g_regression_rollout_helpers_remain_stable() -> None:
    assert normalize_text_with_rollout(
        "90km/h",
        mode="span_default",
        legacy_transform=lambda text: text,
    ) == "시속 구십 킬로미터"
    assert transform_with_rollout(
        "90km/h",
        mode="span_shadow_compare",
        legacy_transform=lambda text: text,
    ) == "90km/h"


def test_phase20g_regression_binary_rollout_helper_can_be_monkeypatched(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    monkeypatch.setattr(binary_runtime, "run_transform_binary", lambda text, binary_path=None: "__binary__")
    assert run_transform_binary_with_rollout("AI") == "__binary__"


def test_phase20g_regression_span_adapter_output_remains_stable() -> None:
    assert transform_for_production("90km/h") == "시속 구십 킬로미터"
