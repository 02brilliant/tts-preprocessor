from __future__ import annotations

import importlib


def test_phase20g_future_server_rollout_helper_invalid_mode_fails() -> None:
    server = importlib.import_module("api.server")
    transform_request_payload = getattr(server, "transform_request_payload")

    try:
        transform_request_payload({"text": "AI", "rollout_mode": "not-a-mode"})
    except ValueError:
        return

    raise AssertionError("transform_request_payload should raise ValueError for invalid rollout_mode")
