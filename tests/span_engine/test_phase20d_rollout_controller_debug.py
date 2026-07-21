from __future__ import annotations

import importlib
import json


def test_phase20d_transform_for_production_debug_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")

    result = adapter.transform_for_production("90km/h", debug=True)

    assert result["ok"] is True
    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert "debug" in result
    json.dumps(result, ensure_ascii=False)


def test_phase20d_transform_payload_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")

    assert adapter.transform_payload({"text": "90km/h"}) == {
        "ok": True,
        "normalized_text": "시속 구십 킬로미터",
    }
