from __future__ import annotations

import importlib


def test_phase22c_actual_legacy_gate_should_pass_after_bracket_review_fix() -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    run_default_rollout_gate = getattr(gate_module, "run_default_rollout_gate")

    compare_module = importlib.import_module("engine.main")
    legacy_transform = getattr(compare_module, "transform")

    result = run_default_rollout_gate(legacy_transform=legacy_transform, strict=False)

    assert result["status"] == "pass"
    assert result["ok"] is True
    assert result["summary"]["suspicious_diff"] == 0
    assert result["summary"]["legacy_error_fixed"] == 0
    assert result["summary"]["unsupported"] == 0
    assert result["blocking_reasons"] == []
    assert result["review_reasons"] == []
