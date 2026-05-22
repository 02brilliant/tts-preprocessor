from __future__ import annotations

import importlib
import json


def test_phase20c_transform_for_production_debug_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    transform_for_production = getattr(adapter, "transform_for_production")

    result = transform_for_production("90km/h", debug=True)

    assert isinstance(result, dict)
    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert "debug" in result or "trace" in result
    json.dumps(result, ensure_ascii=False)


def test_phase20c_transform_payload_debug_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    transform_payload = getattr(adapter, "transform_payload")

    result = transform_payload({"text": "90km/h"}, debug=True)

    assert result["ok"] is True
    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert "debug" in result or "trace" in result

