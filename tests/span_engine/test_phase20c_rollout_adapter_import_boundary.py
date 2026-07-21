from __future__ import annotations

import importlib


def test_phase20c_production_adapter_import_and_transform_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")

    assert adapter.transform_for_production("AI") == "에이아이"
    assert adapter.transform_for_production("90km/h") == "시속 구십 킬로미터"
