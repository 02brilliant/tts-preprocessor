from __future__ import annotations

import importlib


def test_phase20c_transform_for_production_text_mode_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    transform_for_production = getattr(adapter, "transform_for_production")

    assert transform_for_production("90km/h") == "시속 구십 킬로미터"
    assert transform_for_production("60fps") == "육십 에프피에스"
    assert transform_for_production("종로3가") == "종로삼가"
    assert transform_for_production("그리고 우리는 결과를 확인했다") == "그리고, 우리는 결과를 확인했다"


def test_phase20c_transform_for_production_type_guard_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    transform_for_production = getattr(adapter, "transform_for_production")

    for value in (None, b"90km/h", 123):  # type: ignore[arg-type]
        try:
            transform_for_production(value)  # type: ignore[arg-type]
        except TypeError:
            continue
        raise AssertionError(f"expected TypeError for {value!r}")


def test_phase20c_transform_payload_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    transform_payload = getattr(adapter, "transform_payload")

    assert transform_payload({"text": "90km/h"}) == {
        "normalized_text": "시속 구십 킬로미터",
        "ok": True,
    }


def test_phase20c_rollout_mode_helper_contract() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    normalize_rollout_mode = getattr(adapter, "normalize_rollout_mode")

    assert normalize_rollout_mode("legacy_default") == "legacy_default"
    assert normalize_rollout_mode("span_shadow_compare") == "span_shadow_compare"
    assert normalize_rollout_mode("span_default") == "span_default"

    try:
        normalize_rollout_mode("bad-mode")
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid rollout mode")

