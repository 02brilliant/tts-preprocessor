from __future__ import annotations

import importlib
import sys


def test_phase20e_importing_engine_main_does_not_import_production_adapter_yet() -> None:
    before = {name for name in sys.modules if name.startswith("engine.span_engine.production_adapter")}
    module = importlib.import_module("engine.main")
    after = {name for name in sys.modules if name.startswith("engine.span_engine.production_adapter")}

    assert module is not None
    assert after == before
