from __future__ import annotations

import json

from engine.span_engine import compare


def test_phase19b_compare_corpus_entry_model_contract() -> None:
    entry_cls = getattr(compare, "CompareCorpusEntry")

    entry = entry_cls(
        id="same-ai",
        text="AI",
        tags=("canonical",),
        expected_category="same",
        metadata={"source": "smoke"},
    )
    clone = entry_cls(
        id="same-ai-2",
        text="AI",
        tags=("canonical",),
        expected_category="same",
        metadata={"source": "smoke"},
    )

    json.dumps(entry.to_dict(), ensure_ascii=False)
    assert entry.id == "same-ai"
    assert entry.text == "AI"
    assert entry.tags == ("canonical",)
    assert entry.expected_category == "same"
    assert entry.metadata == {"source": "smoke"}
    assert clone.metadata == {"source": "smoke"}


def test_phase19b_compare_corpus_report_model_contract() -> None:
    entry_cls = getattr(compare, "CompareCorpusEntry")
    report_cls = getattr(compare, "CompareCorpusReport")
    result_cls = getattr(compare, "CompareResult")

    entry = entry_cls(
        id="same-ai",
        text="AI",
        tags=("canonical",),
        expected_category="same",
        metadata={},
    )
    result = result_cls(
        input_text="AI",
        legacy_output="에이아이",
        span_output="에이아이",
        equal=True,
        category="same",
        reason="outputs_equal",
        evidence={},
    )
    report = report_cls(entries=[entry], results=[result], summary={}, metadata={})

    json.dumps(report.to_dict(), ensure_ascii=False)
    assert report.entries[0].id == "same-ai"
    assert report.results[0].category == "same"
    assert report.summary == {}
    assert report.metadata == {}


def test_phase19b_compare_corpus_models_have_independent_defaults() -> None:
    entry_cls = getattr(compare, "CompareCorpusEntry")
    report_cls = getattr(compare, "CompareCorpusReport")

    left = entry_cls(id="left", text="A", tags=(), expected_category=None, metadata={})
    right = entry_cls(id="right", text="B", tags=(), expected_category=None, metadata={})
    report_left = report_cls(entries=[left], results=[], summary={}, metadata={})
    report_right = report_cls(entries=[right], results=[], summary={}, metadata={})

    left.metadata["mutated"] = True
    report_left.summary["touched"] = 1

    assert right.metadata == {}
    assert report_right.summary == {}

