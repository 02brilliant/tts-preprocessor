from __future__ import annotations

import json

from engine.span_engine import compare


def test_phase19b_jsonl_export_contract() -> None:
    entry_cls = getattr(compare, "CompareCorpusEntry")
    report_cls = getattr(compare, "CompareCorpusReport")
    result_cls = getattr(compare, "CompareResult")
    export_compare_jsonl = getattr(compare, "export_compare_jsonl")

    report = report_cls(
        entries=[
            entry_cls(id="same-ai", text="AI", tags=("canonical",), expected_category=None, metadata={})
        ],
        results=[
            result_cls(
                input_text="AI",
                legacy_output="에이아이",
                span_output="에이아이",
                equal=True,
                category="same",
                reason="outputs_equal",
                evidence={},
            ),
            result_cls(
                input_text="3~8cm",
                legacy_output="3~8cm",
                span_output="삼에서 팔 센티미터",
                equal=False,
                category="intended_v5_change",
                reason="policy_allowlist",
                evidence={"policy_case": "3~8cm"},
            ),
        ],
        summary={"total": 2, "same": 1, "intended_v5_change": 1, "suspicious_diff": 0, "legacy_error_fixed": 0, "unsupported": 0, "by_category": {"same": 1, "intended_v5_change": 1}},
        metadata={"suite": "smoke"},
    )

    jsonl = export_compare_jsonl(report)
    lines = jsonl.splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["category"] for line in lines] == ["same", "intended_v5_change"]
    assert [json.loads(line)["input_text"] for line in lines] == ["AI", "3~8cm"]
    assert "에이아이" in jsonl
    assert "삼에서 팔 센티미터" in jsonl

