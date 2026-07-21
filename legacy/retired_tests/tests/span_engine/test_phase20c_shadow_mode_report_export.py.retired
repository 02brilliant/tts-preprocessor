from __future__ import annotations

import json

from engine.span_engine.compare import (
    CompareCorpusEntry,
    export_compare_jsonl,
    export_compare_markdown,
    run_compare_corpus,
)
from engine.span_engine.production_adapter import transform_for_production


def test_phase20c_shadow_mode_compare_report_export_regression() -> None:
    entries = [
        CompareCorpusEntry(id="speed", text="90km/h"),
        CompareCorpusEntry(id="ai", text="AI"),
        CompareCorpusEntry(id="guard", text="전문가 유지"),
    ]

    report = run_compare_corpus(
        entries,
        legacy_transform=lambda text: text,
        span_transform=transform_for_production,
        include_debug=True,
    )

    assert report.summary["total"] == 3

    jsonl_text = export_compare_jsonl(report)
    lines = jsonl_text.splitlines()
    assert len(lines) == 3
    for line in lines:
        json.loads(line)

    markdown_text = export_compare_markdown(report)
    assert "# Compare Report" in markdown_text

