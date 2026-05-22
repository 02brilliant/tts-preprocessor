from __future__ import annotations

import importlib
import json


def test_phase20d_run_rollout_transform_debug_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")

    result = run_rollout_transform(
        "90km/h",
        mode="span_default",
        legacy_transform=lambda text: text,
        include_debug=True,
    )

    assert result["mode"] == "span_default"
    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert "debug" in result or "span_debug" in result or "compare" in result
    json.dumps(result, ensure_ascii=False)


def test_phase20d_run_rollout_payload_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_payload = getattr(adapter, "run_rollout_payload")

    result = run_rollout_payload(
        {"text": "90km/h"},
        mode="span_default",
        legacy_transform=lambda text: text,
    )

    assert result["ok"] is True
    assert result["mode"] == "span_default"
    assert result["normalized_text"] == "시속 구십 킬로미터"

