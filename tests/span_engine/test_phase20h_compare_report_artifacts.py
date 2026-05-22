from __future__ import annotations

import json

from engine.span_engine.compare import export_compare_jsonl, export_compare_markdown, run_default_compare_report, write_compare_jsonl, write_compare_markdown


def test_phase20h_compare_report_artifacts_roundtrip(tmp_path) -> None:
    report = run_default_compare_report(legacy_transform=lambda text: text)
    jsonl_path = write_compare_jsonl(report, tmp_path / "report.jsonl")
    markdown_path = write_compare_markdown(report, tmp_path / "report.md")

    assert jsonl_path == tmp_path / "report.jsonl"
    assert markdown_path == tmp_path / "report.md"
    assert jsonl_path.exists()
    assert markdown_path.exists()

    jsonl_text = jsonl_path.read_text(encoding="utf-8")
    markdown_text = markdown_path.read_text(encoding="utf-8")

    assert jsonl_text == export_compare_jsonl(report)
    assert markdown_text == export_compare_markdown(report)
    assert "# Compare Report" in markdown_text
    assert "## Summary" in markdown_text
    assert jsonl_text
    for line in jsonl_text.splitlines():
        json.loads(line)


def test_phase20h_compare_report_artifacts_are_written_within_tmp_path(tmp_path) -> None:
    report = run_default_compare_report(legacy_transform=lambda text: text)
    jsonl_path = write_compare_jsonl(report, tmp_path / "nested" / "report.jsonl")
    markdown_path = write_compare_markdown(report, tmp_path / "nested" / "report.md")

    assert jsonl_path.is_relative_to(tmp_path)
    assert markdown_path.is_relative_to(tmp_path)
