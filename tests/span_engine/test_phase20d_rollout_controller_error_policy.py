from __future__ import annotations

import importlib


def test_phase20d_run_rollout_transform_legacy_default_error_policy() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")

    def failing_legacy(_: str) -> str:
        raise RuntimeError("legacy boom")

    result = run_rollout_transform(
        "90km/h",
        mode="legacy_default",
        legacy_transform=failing_legacy,
    )

    assert result["ok"] is False
    assert result["production_output"] is None
    assert result["error"]


def test_phase20d_run_rollout_transform_span_shadow_compare_legacy_error_policy() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")

    def failing_legacy(_: str) -> str:
        raise RuntimeError("legacy boom")

    result = run_rollout_transform(
        "90km/h",
        mode="span_shadow_compare",
        legacy_transform=failing_legacy,
    )

    assert result["span_output"] == "시속 구십 킬로미터"
    assert result["production_output"] is None
    assert result["compare"]["legacy_error"]
    assert result["compare"]["category"] in {"legacy_error_fixed", "unsupported"}


def test_phase20d_run_rollout_transform_span_default_legacy_error_policy() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")

    def failing_legacy(_: str) -> str:
        raise RuntimeError("legacy boom")

    result = run_rollout_transform(
        "90km/h",
        mode="span_default",
        legacy_transform=failing_legacy,
    )

    assert result["ok"] is True
    assert result["production_output"] == "시속 구십 킬로미터"
    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert result["compare"]["legacy_error"]

