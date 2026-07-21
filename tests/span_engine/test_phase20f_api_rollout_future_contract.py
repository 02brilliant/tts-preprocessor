from __future__ import annotations

import importlib
import inspect


def test_phase20f_api_interface_is_mode_less() -> None:
    api_interface = importlib.import_module("engine.api_interface")

    assert tuple(inspect.signature(api_interface.normalize_text).parameters) == ("text",)
    assert tuple(inspect.signature(api_interface.normalize_text_debug).parameters) == ("text",)
    assert not hasattr(api_interface, "normalize_text_with_rollout")


def test_phase20f_api_text_and_debug_contracts() -> None:
    api_interface = importlib.import_module("engine.api_interface")

    assert api_interface.normalize_text("90km/h") == "시속 구십 킬로미터"
    result = api_interface.normalize_text_debug("90km/h")
    assert result["ok"] is True
    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert "debug" in result
