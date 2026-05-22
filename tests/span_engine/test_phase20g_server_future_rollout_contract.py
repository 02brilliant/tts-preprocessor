from __future__ import annotations

import importlib


def test_phase20g_future_server_rollout_helper_legacy_default_contract(monkeypatch) -> None:
    server = importlib.import_module("api.server")
    transform_request_payload = getattr(server, "transform_request_payload")
    monkeypatch.setattr(
        server,
        "run_transform_binary_with_rollout",
        lambda text, rollout_mode="legacy_default", include_debug=False: "LEGACY:" + text,
    )

    result = transform_request_payload(
        {"text": "90km/h", "rollout_mode": "legacy_default"},
    )

    assert result["normalized_text"] == "LEGACY:90km/h"


def test_phase20g_future_server_rollout_helper_span_default_contract(monkeypatch) -> None:
    server = importlib.import_module("api.server")
    transform_request_payload = getattr(server, "transform_request_payload")
    monkeypatch.setattr(
        server,
        "run_transform_binary_with_rollout",
        lambda text, rollout_mode="legacy_default", include_debug=False: "시속 구십 킬로미터",
    )

    result = transform_request_payload(
        {"text": "90km/h", "rollout_mode": "span_default"},
    )

    assert result["normalized_text"] == "시속 구십 킬로미터"


def test_phase20g_future_server_rollout_helper_shadow_debug_contract(monkeypatch) -> None:
    server = importlib.import_module("api.server")
    transform_request_payload = getattr(server, "transform_request_payload")
    monkeypatch.setattr(
        server,
        "run_transform_binary_with_rollout",
        lambda text, rollout_mode="legacy_default", include_debug=False: {
            "ok": True,
            "mode": rollout_mode,
            "normalized_text": "90km/h",
        },
    )

    result = transform_request_payload(
        {
            "text": "90km/h",
            "rollout_mode": "span_shadow_compare",
            "include_debug": True,
        },
    )

    assert result["normalized_text"] == "90km/h"
    assert result["mode"] == "span_shadow_compare"
