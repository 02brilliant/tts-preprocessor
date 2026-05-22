from __future__ import annotations

from engine.span_engine import compare


def test_phase19b_run_compare_corpus_contract_with_injected_callables() -> None:
    entry_cls = getattr(compare, "CompareCorpusEntry")
    run_compare_corpus = getattr(compare, "run_compare_corpus")

    entries = [
        entry_cls(id="same-ai", text="AI", tags=("canonical",), expected_category=None, metadata={}),
        entry_cls(
            id="intended-range",
            text="3~8cm",
            tags=("intended_diff",),
            expected_category=None,
            metadata={},
        ),
        entry_cls(
            id="suspicious",
            text="전문가 유지",
            tags=("suspicious_guard",),
            expected_category=None,
            metadata={},
        ),
        entry_cls(
            id="legacy-error",
            text="legacy fails",
            tags=("legacy_error",),
            expected_category=None,
            metadata={},
        ),
        entry_cls(
            id="span-error",
            text="span fails",
            tags=("span_error",),
            expected_category=None,
            metadata={},
        ),
    ]

    def legacy_transform(text: str) -> str:
        if text == "legacy fails":
            raise RuntimeError("legacy boom")
        mapping = {
            "AI": "에이아이",
            "3~8cm": "3~8cm",
            "전문가 유지": "전문가 유지",
            "span fails": "span fails",
        }
        return mapping[text]

    def span_transform(text: str) -> str:
        if text == "span fails":
            raise RuntimeError("span boom")
        mapping = {
            "AI": "에이아이",
            "3~8cm": "삼에서 팔 센티미터",
            "전문가 유지": "전문이 유지",
            "legacy fails": "legacy stable",
        }
        return mapping[text]

    report = run_compare_corpus(
        entries,
        legacy_transform=legacy_transform,
        span_transform=span_transform,
        include_debug=True,
    )

    assert [result.input_text for result in report.results] == [entry.text for entry in entries]
    assert [result.category for result in report.results] == [
        "same",
        "intended_v5_change",
        "suspicious_diff",
        "legacy_error_fixed",
        "suspicious_diff",
    ]
    assert report.summary["total"] == 5
    assert report.summary["same"] == 1
    assert report.summary["intended_v5_change"] == 1
    assert report.summary["suspicious_diff"] == 2
    assert report.summary["legacy_error_fixed"] == 1
    assert report.summary["unsupported"] == 0
    assert report.summary["intended_count"] == 1
    assert report.summary["suspicious_count"] == 2
    assert report.results[0].span_debug is not None
    assert report.results[1].span_debug is not None
    assert report.results[2].span_error is None
    assert report.results[3].legacy_error == "legacy boom"
    assert report.results[4].span_error == "span boom"
    assert report.entries[0].id == "same-ai"
    assert report.entries[1].id == "intended-range"
    assert report.entries[2].id == "suspicious"
    assert report.entries[3].id == "legacy-error"
    assert report.entries[4].id == "span-error"


def test_phase19b_run_compare_corpus_with_span_transform_integration() -> None:
    entry_cls = getattr(compare, "CompareCorpusEntry")
    run_compare_corpus = getattr(compare, "run_compare_corpus")

    report = run_compare_corpus(
        [entry_cls(id="span", text="90km/h", tags=("canonical",), expected_category=None, metadata={})],
        legacy_transform=lambda text: text,
        include_debug=True,
    )

    assert report.results[0].span_output == "시속 구십 킬로미터"
    assert report.results[0].span_debug is not None
    assert report.results[0].category in {"intended_v5_change", "suspicious_diff"}

