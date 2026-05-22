from __future__ import annotations

import json

from engine.span_engine import compare


def test_phase19c_run_default_compare_report_with_injected_legacy_callable() -> None:
    run_default_compare_report = getattr(compare, "run_default_compare_report")
    build_default_compare_corpus = getattr(compare, "build_default_compare_corpus")

    corpus = build_default_compare_corpus()
    report = run_default_compare_report(
        legacy_transform=lambda text: text,
        include_debug=True,
    )

    json.dumps(report.to_dict(), ensure_ascii=False)
    assert report.summary["total"] == len(corpus)
    assert [result.input_text for result in report.results] == [entry.text for entry in corpus]
    assert any(result.category == "intended_v5_change" for result in report.results)
    assert all(result.span_error is None for result in report.results)
    assert all(result.span_debug is not None for result in report.results)


def test_phase19c_resolve_legacy_transform_is_optional_and_graceful(monkeypatch) -> None:
    resolve_legacy_transform = getattr(compare, "resolve_legacy_transform")

    monkeypatch.setattr(compare, "get_optional_legacy_transform", lambda: None)
    assert resolve_legacy_transform() is None


def test_phase19c_run_compare_corpus_uses_optional_getter_only_when_needed(monkeypatch) -> None:
    entry_cls = getattr(compare, "CompareCorpusEntry")

    called = {"getter": 0}

    def fake_getter():
        called["getter"] += 1
        return None

    monkeypatch.setattr(compare, "get_optional_legacy_transform", fake_getter)

    report = compare.run_compare_corpus(
        [entry_cls(id="x", text="안녕하세요", tags=(), expected_category=None, metadata={})],
        span_transform=lambda text: text,
    )

    assert called["getter"] == 1
    assert report.summary["total"] == 1
    assert report.results[0].category in {"same", "unsupported"}

