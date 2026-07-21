from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "removed_mode",
    ["retired_mode", "span_default", "unsupported_mode"],
)
def test_phase20g_server_rejects_removed_rollout_field(
    removed_mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = importlib.import_module("api.server")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("removed rollout field reached binary execution")

    monkeypatch.setattr(server, "run_transform_binary", fail_if_called)
    monkeypatch.setattr(server, "run_transform_binary_debug", fail_if_called)

    with pytest.raises(ValueError, match="not supported"):
        server.transform_request_payload(
            {"text": "90km/h", "rollout_mode": removed_mode},
        )


def test_phase20g_server_mode_less_debug_contract(monkeypatch) -> None:
    server = importlib.import_module("api.server")
    monkeypatch.setattr(
        server,
        "run_transform_binary_debug",
        lambda text: {"ok": True, "normalized_text": "시속 구십 킬로미터", "debug": {}},
    )

    result = server.transform_request_payload(
        {"text": "90km/h", "include_debug": True},
    )

    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert result["debug"] == {}
