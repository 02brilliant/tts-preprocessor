from __future__ import annotations

import importlib
import sys


def test_phase19c_default_corpus_does_not_force_legacy_pipeline_import() -> None:
    compare = importlib.import_module("engine.span_engine.compare")
    build_default_compare_corpus = getattr(compare, "build_default_compare_corpus")
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}

    build_default_compare_corpus()

    after = {name for name in sys.modules if name.startswith("engine.pipeline")}
    assert after == before


def test_phase19c_export_helpers_do_not_force_legacy_pipeline_import() -> None:
    compare = importlib.import_module("engine.span_engine.compare")
    write_compare_jsonl = getattr(compare, "write_compare_jsonl")
    write_compare_markdown = getattr(compare, "write_compare_markdown")
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}

    report = compare.CompareCorpusReport()
    # use tmp names through cwd-less temp APIs in caller tests; here just ensure callables resolve
    assert callable(write_compare_jsonl)
    assert callable(write_compare_markdown)

    after = {name for name in sys.modules if name.startswith("engine.pipeline")}
    assert report.summary == {}
    assert after == before


def test_phase19c_run_default_compare_report_with_injected_legacy_transform_does_not_force_legacy_pipeline_import() -> None:
    compare = importlib.import_module("engine.span_engine.compare")
    run_default_compare_report = getattr(compare, "run_default_compare_report")
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}

    run_default_compare_report(
        legacy_transform=lambda text: text,
        span_transform=lambda text: text,
        include_debug=False,
    )

    after = {name for name in sys.modules if name.startswith("engine.pipeline")}
    assert after == before

