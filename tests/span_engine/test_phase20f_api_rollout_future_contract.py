from __future__ import annotations

import importlib


def test_phase20f_future_api_rollout_helper_legacy_default_contract() -> None:
    api_interface = importlib.import_module("engine.api_interface")
    normalize_text_with_rollout = getattr(api_interface, "normalize_text_with_rollout")

    result = normalize_text_with_rollout(
        "90km/h",
        legacy_transform=lambda text: "LEGACY:" + text,
    )

    assert result == "LEGACY:90km/h"


def test_phase20f_future_api_rollout_helper_shadow_debug_contract() -> None:
    api_interface = importlib.import_module("engine.api_interface")
    normalize_text_with_rollout = getattr(api_interface, "normalize_text_with_rollout")

    result = normalize_text_with_rollout(
        "90km/h",
        mode="span_shadow_compare",
        include_debug=True,
        legacy_transform=lambda text: text,
    )

    assert result["normalized_text"] == "90km/h"
    assert result["span_output"] == "시속 구십 킬로미터"
    assert result["compare"]["category"] == "intended_v5_change"


def test_phase20f_future_api_rollout_helper_span_default_contract() -> None:
    api_interface = importlib.import_module("engine.api_interface")
    normalize_text_with_rollout = getattr(api_interface, "normalize_text_with_rollout")

    result = normalize_text_with_rollout(
        "90km/h",
        mode="span_default",
        include_debug=True,
        legacy_transform=lambda text: text,
    )

    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert result["compare"]["category"] == "intended_v5_change"
