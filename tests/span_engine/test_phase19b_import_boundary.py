from __future__ import annotations

import importlib
import sys


def test_phase19b_compare_module_import_does_not_force_legacy_pipeline_import() -> None:
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}
    module = importlib.import_module("engine.span_engine.compare")
    after = {name for name in sys.modules if name.startswith("engine.pipeline")}

    assert module is not None
    assert after == before


def test_phase19b_compare_runner_uses_injected_legacy_callable_only() -> None:
    compare = importlib.import_module("engine.span_engine.compare")
    run_compare_corpus = getattr(compare, "run_compare_corpus")
    entry_cls = getattr(compare, "CompareCorpusEntry")

    called = {"legacy": 0}

    def legacy_transform(text: str) -> str:
        called["legacy"] += 1
        return text

    def span_transform(text: str) -> str:
        return text

    report = run_compare_corpus(
        [entry_cls(id="x", text="안녕하세요", tags=(), expected_category=None, metadata={})],
        legacy_transform=legacy_transform,
        span_transform=span_transform,
    )

    assert called["legacy"] == 1
    assert report.results[0].category == "same"


def test_phase19b_normal_transform_path_does_not_depend_on_compare_runner() -> None:
    from engine.span_engine import transform

    assert transform("안녕하세요") == "안녕하세요"

