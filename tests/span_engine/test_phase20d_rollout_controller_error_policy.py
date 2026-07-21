from __future__ import annotations

import importlib


def test_phase20d_production_adapter_has_only_current_callback_surface() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")

    assert adapter.transform_for_production("90km/h") == "시속 구십 킬로미터"
    assert tuple(adapter.transform_for_production.__annotations__) == (
        "text",
        "enable_prosody",
        "debug",
        "return",
    )
