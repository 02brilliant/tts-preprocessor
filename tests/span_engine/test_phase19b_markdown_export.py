from __future__ import annotations

from engine.span_engine import compare


def test_phase19b_markdown_export_contract() -> None:
    entry_cls = getattr(compare, "CompareCorpusEntry")
    report_cls = getattr(compare, "CompareCorpusReport")
    result_cls = getattr(compare, "CompareResult")
    export_compare_markdown = getattr(compare, "export_compare_markdown")

    report = report_cls(
        entries=[
            entry_cls(id="pipe", text="A|B", tags=("canonical",), expected_category=None, metadata={}),
            entry_cls(id="suspicious", text="[3kg]", tags=("bracket",), expected_category=None, metadata={}),
            entry_cls(id="intended", text="3~8cm", tags=("intended_diff",), expected_category=None, metadata={}),
        ],
        results=[
            result_cls(
                input_text="A|B",
                legacy_output="A|B",
                span_output="A|B",
                equal=True,
                category="same",
                reason="outputs_equal",
                evidence={},
            ),
            result_cls(
                input_text="[3kg]",
                legacy_output="3kg",
                span_output="삼 킬로그램",
                equal=False,
                category="suspicious_diff",
                reason="bracket_protection",
                evidence={"rule": "bracket_protection"},
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
        summary={
            "total": 3,
            "same": 1,
            "intended_v5_change": 1,
            "suspicious_diff": 1,
            "legacy_error_fixed": 0,
            "unsupported": 0,
            "by_category": {"same": 1, "intended_v5_change": 1, "suspicious_diff": 1},
        },
        metadata={"suite": "smoke"},
    )

    markdown = export_compare_markdown(report)

    assert "# Compare Report" in markdown or "## Summary" in markdown
    assert "suspicious_diff" in markdown
    assert "intended_v5_change" in markdown
    assert "A\\|B" in markdown or "A|B" not in markdown.splitlines()[0]
    assert "삼에서 팔 센티미터" in markdown
    assert "[3kg]" in markdown


def test_phase19b_markdown_export_does_not_dump_large_debug_by_default() -> None:
    entry_cls = getattr(compare, "CompareCorpusEntry")
    report_cls = getattr(compare, "CompareCorpusReport")
    result_cls = getattr(compare, "CompareResult")
    export_compare_markdown = getattr(compare, "export_compare_markdown")

    report = report_cls(
        entries=[entry_cls(id="same-ai", text="AI", tags=(), expected_category=None, metadata={})],
        results=[
            result_cls(
                input_text="AI",
                legacy_output="에이아이",
                span_output="에이아이",
                equal=True,
                category="same",
                reason="outputs_equal",
                evidence={},
                span_debug={"normalized_text": "에이아이", "trace": {"claim_logs": []}},
            )
        ],
        summary={"total": 1, "same": 1, "intended_v5_change": 0, "suspicious_diff": 0, "legacy_error_fixed": 0, "unsupported": 0, "by_category": {"same": 1}},
        metadata={},
    )

    markdown = export_compare_markdown(report)

    assert "claim_logs" not in markdown
    assert "normalized_text" not in markdown or markdown.count("normalized_text") <= 1

