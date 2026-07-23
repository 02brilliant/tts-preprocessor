from __future__ import annotations

import importlib

from engine.span_engine.compare import CompareCorpusEntry, CompareCorpusReport, CompareResult


def test_phase20h_gate_helper_result_shape_contract() -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    build_rollout_gate_result = getattr(gate_module, "build_rollout_gate_result")

    report = CompareCorpusReport(
        entries=[CompareCorpusEntry(id="ok", text="AI")],
        results=[
            CompareResult(
                input_text="AI",
                legacy_output="에이아이",
                span_output="에이아이",
                equal=True,
                category="same",
                reason="outputs_equal",
                evidence={},
            )
        ],
        summary={
            "total": 1,
            "same": 1,
            "intended_v5_change": 0,
            "suspicious_diff": 0,
            "legacy_error_fixed": 0,
            "unsupported": 0,
            "by_category": {
                "same": 1,
                "intended_v5_change": 0,
                "suspicious_diff": 0,
                "legacy_error_fixed": 0,
                "unsupported": 0,
            },
            "suspicious_count": 0,
            "intended_count": 0,
        },
    )

    result = build_rollout_gate_result(report)

    assert set(result) >= {"ok", "status", "summary", "blocking_reasons", "review_reasons", "report", "artifacts"}
    assert result["status"] == "pass"
    assert result["ok"] is True


def test_phase20h_gate_helper_invalid_mode_less_contract_is_not_needed() -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    assert getattr(gate_module, "build_rollout_gate_result")
