from __future__ import annotations

import json

from engine.span_engine.compare import build_default_compare_corpus, export_compare_jsonl, export_compare_markdown, run_default_compare_report


def test_phase20h_default_compare_corpus_gate_summary_and_order() -> None:
    corpus = build_default_compare_corpus()
    report = run_default_compare_report(legacy_transform=lambda text: text)

    assert corpus
    assert report.summary["total"] == len(corpus)
    assert [entry.id for entry in report.entries] == [entry.id for entry in corpus]
    assert report.summary["intended_v5_change"] >= 1
    assert report.summary["suspicious_diff"] == 0
    assert report.summary["unsupported"] == 0
    assert all(result.span_error is None for result in report.results)

    payload = report.to_dict()
    json.dumps(payload, ensure_ascii=False)

    jsonl = export_compare_jsonl(report)
    markdown = export_compare_markdown(report)

    assert jsonl.count("\n") == len(report.results) - 1
    assert markdown.startswith("# Compare Report")
    assert "## Intended V5 Changes" in markdown
    assert "## Suspicious Diffs" not in markdown


def test_phase20h_default_compare_corpus_gate_review_items_are_cleared_after_classifier_fix() -> None:
    report = run_default_compare_report(legacy_transform=lambda text: text)

    suspicious = [result for result in report.results if result.category == "suspicious_diff"]
    intended = [result for result in report.results if result.category == "intended_v5_change"]

    assert suspicious == []
    assert intended
    assert all(result.evidence.get("entry_id") for result in report.results)
    assert all(result.evidence.get("expected_category_mismatch") is not True for result in report.results)
