from __future__ import annotations

import importlib
import sys


def test_phase20g_importing_server_does_not_import_production_adapter_directly_in_current_state() -> None:
    before = {name for name in sys.modules if name.startswith("engine.span_engine.production_adapter")}
    module = importlib.import_module("api.server")
    after = {name for name in sys.modules if name.startswith("engine.span_engine.production_adapter")}

    assert module is not None
    assert after == before
