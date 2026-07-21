from __future__ import annotations

import importlib


def test_phase20e_engine_main_exports_only_mode_less_facades() -> None:
    engine_main = importlib.import_module("engine.main")

    assert engine_main.__all__ == ["transform", "transform_debug"]
    assert engine_main.transform("90km/h") == "시속 구십 킬로미터"
    assert engine_main.transform_debug("90km/h")["normalized_text"] == "시속 구십 킬로미터"
