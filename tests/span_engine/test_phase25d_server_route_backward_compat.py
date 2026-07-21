from __future__ import annotations

import pytest

import api.server as server


def test_phase25d_removed_rollout_payload_is_rejected(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("removed rollout payload reached binary execution")

    monkeypatch.setattr(server, "run_transform_binary", fail_if_called)
    monkeypatch.setattr(server, "run_transform_binary_debug", fail_if_called)

    with pytest.raises(ValueError, match="not supported"):
        server.transform_request_payload(
            {"text": "90km/h", "rollout_mode": "span_default"}
        )
