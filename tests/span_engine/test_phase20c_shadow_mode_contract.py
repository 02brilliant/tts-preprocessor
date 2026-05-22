from __future__ import annotations

import importlib


def test_phase20c_run_shadow_compare_intended_diff_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_shadow_compare = getattr(adapter, "run_shadow_compare")

    result = run_shadow_compare("90km/h", legacy_transform=lambda text: text)

    assert result["input_text"] == "90km/h"
    assert result["legacy_output"] == "90km/h"
    assert result["span_output"] == "시속 구십 킬로미터"
    assert result["production_output"] == "90km/h"
    assert result["category"] == "intended_v5_change"
    assert result["equal"] is False
    assert result["shadow"] is True
    assert result["legacy_error"] is None
    assert result["span_error"] is None


def test_phase20c_run_shadow_compare_same_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_shadow_compare = getattr(adapter, "run_shadow_compare")

    result = run_shadow_compare("AI", legacy_transform=lambda text: "에이아이")

    assert result["legacy_output"] == "에이아이"
    assert result["span_output"] == "에이아이"
    assert result["production_output"] == "에이아이"
    assert result["category"] == "same"
    assert result["equal"] is True
    assert result["shadow"] is True


def test_phase20c_run_shadow_compare_legacy_error_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_shadow_compare = getattr(adapter, "run_shadow_compare")

    def failing_legacy(_: str) -> str:
        raise RuntimeError("legacy boom")

    result = run_shadow_compare("90km/h", legacy_transform=failing_legacy)

    assert result["span_output"] == "시속 구십 킬로미터"
    assert result["legacy_error"]
    assert result["category"] in {"legacy_error_fixed", "unsupported"}
    assert result["shadow"] is True


def test_phase20c_build_shadow_compare_payload_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    build_shadow_compare_payload = getattr(adapter, "build_shadow_compare_payload")

    result = build_shadow_compare_payload(
        {"text": "90km/h"},
        legacy_transform=lambda text: text,
    )

    assert result["ok"] is True
    assert result["mode"] == "span_shadow_compare"
    assert result["normalized_text"] == "90km/h"
    assert result["legacy_output"] == "90km/h"
    assert result["span_output"] == "시속 구십 킬로미터"
    assert result["compare"]["category"] == "intended_v5_change"

