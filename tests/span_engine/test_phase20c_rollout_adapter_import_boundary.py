from __future__ import annotations

import importlib
import sys


def test_phase20c_importing_production_adapter_does_not_force_legacy_pipeline_import() -> None:
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}
    module = importlib.import_module("engine.span_engine.production_adapter")
    after = {name for name in sys.modules if name.startswith("engine.pipeline")}

    assert module is not None
    assert after == before


def test_phase20c_transform_for_production_does_not_force_legacy_pipeline_import() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    transform_for_production = getattr(adapter, "transform_for_production")
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}

    transform_for_production("90km/h")

    after = {name for name in sys.modules if name.startswith("engine.pipeline")}
    assert after == before

