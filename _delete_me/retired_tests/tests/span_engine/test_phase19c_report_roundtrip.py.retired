from __future__ import annotations

import json

from engine.span_engine import compare


def test_phase19c_compare_report_roundtrip_contract() -> None:
    report_cls = getattr(compare, "CompareCorpusReport")
    entry_cls = getattr(compare, "CompareCorpusEntry")
    result_cls = getattr(compare, "CompareResult")

    results = [
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
    ]
    report = report_cls(
        entries=[
            entry_cls(id="same-ai", text="AI", tags=("canonical",), expected_category=None, metadata={}),
            entry_cls(id="range", text="3~8cm", tags=("range",), expected_category=None, metadata={}),
        ],
        results=results,
        summary=compare.build_compare_summary(results),
        metadata={"suite": "roundtrip"},
    )

    payload = report.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False)
    decoded = json.loads(encoded)
    restored = report_cls.from_dict(decoded)

    assert restored.summary == report.summary
    assert len(restored.entries) == len(report.entries)
    assert len(restored.results) == len(report.results)
    assert [result.category for result in restored.results] == [result.category for result in report.results]

