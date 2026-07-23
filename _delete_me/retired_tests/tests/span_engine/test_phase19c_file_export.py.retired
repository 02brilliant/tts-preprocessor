from __future__ import annotations

from engine.span_engine import compare


def test_phase19c_write_compare_jsonl_file(tmp_path) -> None:
    write_compare_jsonl = getattr(compare, "write_compare_jsonl")
    entry_cls = getattr(compare, "CompareCorpusEntry")
    report_cls = getattr(compare, "CompareCorpusReport")
    result_cls = getattr(compare, "CompareResult")

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
        summary=compare.build_compare_summary(
            [
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
        ),
        metadata={},
    )

    path = tmp_path / "compare" / "report.jsonl"
    written = write_compare_jsonl(report, path)

    assert path.exists()
    assert written == path or str(written) == str(path)
    contents = path.read_text(encoding="utf-8")
    assert contents == compare.export_compare_jsonl(report)
    assert "삼에서 팔 센티미터" in contents
    assert len(contents.splitlines()) == len(report.results)


def test_phase19c_write_compare_markdown_file(tmp_path) -> None:
    write_compare_markdown = getattr(compare, "write_compare_markdown")
    entry_cls = getattr(compare, "CompareCorpusEntry")
    report_cls = getattr(compare, "CompareCorpusReport")
    result_cls = getattr(compare, "CompareResult")

    results = [
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
            entry_cls(id="pipe", text="A|B", tags=("canonical",), expected_category=None, metadata={}),
            entry_cls(id="range", text="3~8cm", tags=("range", "intended_diff"), expected_category=None, metadata={}),
        ],
        results=results,
        summary=compare.build_compare_summary(results),
        metadata={},
    )

    path = tmp_path / "compare" / "report.md"
    written = write_compare_markdown(report, path)

    assert path.exists()
    assert written == path or str(written) == str(path)
    contents = path.read_text(encoding="utf-8")
    assert contents == compare.export_compare_markdown(report)
    assert "# Compare Report" in contents or "## Summary" in contents
    assert "삼에서 팔 센티미터" in contents

