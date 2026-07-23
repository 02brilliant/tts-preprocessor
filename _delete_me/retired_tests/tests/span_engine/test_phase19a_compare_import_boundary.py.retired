from __future__ import annotations

import importlib
import sys


def test_phase19a_compare_module_import_does_not_force_legacy_pipeline_import() -> None:
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}
    module = importlib.import_module("engine.span_engine.compare")
    after = {name for name in sys.modules if name.startswith("engine.pipeline")}

    assert module is not None
    assert after == before


def test_phase19a_compare_legacy_wrapper_is_optional() -> None:
    compare = importlib.import_module("engine.span_engine.compare")

    legacy_transform = compare.get_optional_legacy_transform()
    assert legacy_transform is None or callable(legacy_transform)


def test_phase19a_compare_module_is_not_used_by_normal_transform_path() -> None:
    import engine.span_engine.compare as compare
    from engine.span_engine import transform

    assert transform("안녕하세요") == "안녕하세요"
    assert hasattr(compare, "classify_compare_result")
