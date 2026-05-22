from __future__ import annotations

import importlib
import sys


def test_phase20d_importing_production_adapter_does_not_force_legacy_pipeline_import() -> None:
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}
    module = importlib.import_module("engine.span_engine.production_adapter")
    after = {name for name in sys.modules if name.startswith("engine.pipeline")}

    assert module is not None
    assert after == before


def test_phase20d_run_rollout_transform_identity_fallback_does_not_force_legacy_pipeline_import() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}

    run_rollout_transform("AI", mode="legacy_default")

    after = {name for name in sys.modules if name.startswith("engine.pipeline")}
    assert after == before


def test_phase20d_run_rollout_transform_shadow_with_injected_legacy_transform_does_not_force_legacy_pipeline_import() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    run_rollout_transform = getattr(adapter, "run_rollout_transform")
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}

    run_rollout_transform(
        "90km/h",
        mode="span_shadow_compare",
        legacy_transform=lambda text: text,
    )

    after = {name for name in sys.modules if name.startswith("engine.pipeline")}
    assert after == before

