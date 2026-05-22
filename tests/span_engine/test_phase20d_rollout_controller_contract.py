from __future__ import annotations

import importlib


def test_phase20d_run_rollout_transform_legacy_default_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")

    result = run_rollout_transform(
        "90km/h",
        mode="legacy_default",
        legacy_transform=lambda text: "LEGACY:" + text,
    )

    assert result["ok"] is True
    assert result["mode"] == "legacy_default"
    assert result["input_text"] == "90km/h"
    assert result["production_output"] == "LEGACY:90km/h"
    assert result["normalized_text"] == "LEGACY:90km/h"
    assert result["legacy_output"] == "LEGACY:90km/h"
    assert result["span_output"] is None
    assert result["compare"] is None


def test_phase20d_run_rollout_transform_span_shadow_compare_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")

    result = run_rollout_transform(
        "90km/h",
        mode="span_shadow_compare",
        legacy_transform=lambda text: text,
    )

    assert result["ok"] is True
    assert result["mode"] == "span_shadow_compare"
    assert result["legacy_output"] == "90km/h"
    assert result["span_output"] == "시속 구십 킬로미터"
    assert result["production_output"] == "90km/h"
    assert result["normalized_text"] == "90km/h"
    assert result["compare"]["category"] == "intended_v5_change"


def test_phase20d_run_rollout_transform_span_default_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")

    result = run_rollout_transform(
        "90km/h",
        mode="span_default",
        legacy_transform=lambda text: text,
    )

    assert result["ok"] is True
    assert result["mode"] == "span_default"
    assert result["span_output"] == "시속 구십 킬로미터"
    assert result["production_output"] == "시속 구십 킬로미터"
    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert result["legacy_output"] == "90km/h"
    assert result["compare"]["category"] == "intended_v5_change"


def test_phase20d_run_rollout_transform_legacy_default_identity_fallback_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")

    result = run_rollout_transform("AI", mode="legacy_default")

    assert result["ok"] is True
    assert result["normalized_text"] == "AI"
    assert result["production_output"] == "AI"

