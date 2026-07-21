from __future__ import annotations

import importlib


def test_phase21c_default_rollout_gate_should_pass_after_review() -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    run_default_rollout_gate = getattr(gate_module, "run_default_rollout_gate")

    result = run_default_rollout_gate(legacy_transform=lambda text: text)

    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["summary"]["suspicious_diff"] == 0
    assert result["review_reasons"] == []
    assert result["blocking_reasons"] == []


def test_phase21c_default_rollout_gate_should_not_need_artifacts_for_pass() -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    run_default_rollout_gate = getattr(gate_module, "run_default_rollout_gate")

    result = run_default_rollout_gate(legacy_transform=lambda text: text, strict=False)

    assert result["status"] == "pass"
    assert result["artifacts"] is None
