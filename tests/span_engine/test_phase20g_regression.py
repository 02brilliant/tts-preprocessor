from __future__ import annotations

from api.binary_runtime import run_transform_binary
from engine.api_interface import normalize_text
from engine.main import transform
from engine.span_engine.production_adapter import transform_for_production


def test_phase20g_regression_mode_less_helpers_remain_stable() -> None:
    assert normalize_text("90km/h") == "시속 구십 킬로미터"
    assert transform("90km/h") == "시속 구십 킬로미터"


def test_phase20g_regression_binary_helper_can_be_monkeypatched(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    monkeypatch.setattr(binary_runtime, "run_transform_binary", lambda text, binary_path=None: "__binary__")
    assert binary_runtime.run_transform_binary("AI") == "__binary__"


def test_phase20g_regression_span_adapter_output_remains_stable() -> None:
    assert transform_for_production("90km/h") == "시속 구십 킬로미터"
