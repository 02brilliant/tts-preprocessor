from __future__ import annotations

import importlib

from engine.span_engine.compare import build_default_compare_corpus, run_default_compare_report


def test_phase20h_default_rollout_gate_pass_contract_after_classifier_review_fix() -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    run_default_rollout_gate = getattr(gate_module, "run_default_rollout_gate")

    result = run_default_rollout_gate(legacy_transform=lambda text: text)

    assert result["status"] == "pass"
    assert result["ok"] is True
    assert result["summary"]["total"] == len(build_default_compare_corpus())
    assert result["summary"]["suspicious_diff"] == 0
    assert result["review_reasons"] == []
    assert result["blocking_reasons"] == []
    assert result["artifacts"] is None


def test_phase20h_default_rollout_gate_artifact_dir_contract(tmp_path) -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    run_default_rollout_gate = getattr(gate_module, "run_default_rollout_gate")

    result = run_default_rollout_gate(legacy_transform=lambda text: text, artifact_dir=tmp_path)

    assert result["status"] == "pass"
    assert result["artifacts"] is not None
    assert result["artifacts"]["jsonl"].is_file()
    assert result["artifacts"]["markdown"].is_file()
    assert result["artifacts"]["jsonl"].is_relative_to(tmp_path)
    assert result["artifacts"]["markdown"].is_relative_to(tmp_path)


def test_phase20h_pass_and_fail_policy_can_be_represented_with_synthetic_reports() -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    build_rollout_gate_result = getattr(gate_module, "build_rollout_gate_result")

    same_report = run_default_compare_report(legacy_transform=lambda text: text)
    same_report.summary["suspicious_diff"] = 0
    same_report.summary["legacy_error_fixed"] = 0
    same_report.summary["unsupported"] = 0
    result = build_rollout_gate_result(same_report)
    assert result["status"] in {"pass", "review_required"}
