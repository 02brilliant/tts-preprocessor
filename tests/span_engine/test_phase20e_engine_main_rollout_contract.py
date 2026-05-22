from __future__ import annotations

import importlib


def test_phase20e_future_transform_with_rollout_default_returns_legacy_output() -> None:
    engine_main = importlib.import_module("engine.main")
    transform_with_rollout = getattr(engine_main, "transform_with_rollout")

    result = transform_with_rollout(
        "90km/h",
        legacy_transform=lambda text: "LEGACY:" + text,
    )

    assert result == "LEGACY:90km/h"


def test_phase20e_future_transform_with_rollout_shadow_debug_contract() -> None:
    engine_main = importlib.import_module("engine.main")
    transform_with_rollout = getattr(engine_main, "transform_with_rollout")

    result = transform_with_rollout(
        "90km/h",
        mode="span_shadow_compare",
        include_debug=True,
        legacy_transform=lambda text: text,
    )

    assert result["normalized_text"] == "90km/h"
    assert result["span_output"] == "시속 구십 킬로미터"
    assert result["compare"]["category"] == "intended_v5_change"


def test_phase20e_future_transform_with_rollout_span_default_contract() -> None:
    engine_main = importlib.import_module("engine.main")
    transform_with_rollout = getattr(engine_main, "transform_with_rollout")

    result = transform_with_rollout(
        "90km/h",
        mode="span_default",
        include_debug=True,
        legacy_transform=lambda text: text,
    )

    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert result["legacy_output"] == "90km/h"
    assert result["compare"]["category"] == "intended_v5_change"


def test_phase20e_future_transform_with_rollout_invalid_mode_raises_value_error() -> None:
    engine_main = importlib.import_module("engine.main")
    transform_with_rollout = getattr(engine_main, "transform_with_rollout")

    try:
        transform_with_rollout("AI", mode="not-a-mode")
    except ValueError:
        return

    raise AssertionError("transform_with_rollout should raise ValueError for invalid mode")
