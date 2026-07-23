from __future__ import annotations

import importlib

from engine.span_engine.compare import CompareCorpusEntry, CompareCorpusReport, CompareResult


def test_phase20h_rollout_gate_helper_policy_statuses() -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    build_rollout_gate_result = getattr(gate_module, "build_rollout_gate_result")

    def make_report(category: str, *, span_error: str | None = None) -> CompareCorpusReport:
        return CompareCorpusReport(
            entries=[CompareCorpusEntry(id="x", text="x")],
            results=[
                CompareResult(
                    input_text="x",
                    legacy_output="x",
                    span_output="x",
                    equal=(category == "same"),
                    category=category,
                    reason=category,
                    evidence={},
                    span_error=span_error,
                )
            ],
            summary={
                "total": 1,
                "same": 0,
                "intended_v5_change": 0,
                "suspicious_diff": 0,
                "legacy_error_fixed": 0,
                "unsupported": 0,
                "by_category": {
                    "same": 0,
                    "intended_v5_change": 0,
                    "suspicious_diff": 0,
                    "legacy_error_fixed": 0,
                    "unsupported": 0,
                },
                "suspicious_count": 0,
                "intended_count": 0,
            },
        )

    assert build_rollout_gate_result(make_report("same"))["status"] in {"pass", "review_required"}
    assert build_rollout_gate_result(make_report("intended_v5_change"))["status"] in {"pass", "review_required"}
    assert build_rollout_gate_result(make_report("suspicious_diff"))["status"] == "review_required"
    assert build_rollout_gate_result(make_report("legacy_error_fixed"))["status"] == "review_required"
    assert build_rollout_gate_result(make_report("unsupported"))["status"] == "review_required"
    assert build_rollout_gate_result(make_report("suspicious_diff", span_error="boom"))["status"] == "fail"
