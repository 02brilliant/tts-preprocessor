from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_phase25d_default_request_uses_mode_less_binary(monkeypatch) -> None:
    import api.server as server

    seen: list[str] = []

    def fake_run_transform_binary(text: str) -> str:
        seen.append(text)
        return "에이아이"

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)

    client = TestClient(server.app)
    response = client.post("/api/transform", json={"text": "AI"})

    assert response.status_code == 200
    assert response.json() == {"normalized_text": "에이아이"}
    assert seen == ["AI"]


def test_phase25d_include_debug_uses_mode_less_debug_binary(monkeypatch) -> None:
    import api.server as server

    seen: list[str] = []

    def fake_debug(text: str) -> dict:
        seen.append(text)
        return {"ok": True, "normalized_text": "에이아이", "debug": {"trace": {}}}

    monkeypatch.setattr(server, "run_transform_binary_debug", fake_debug)
    client = TestClient(server.app)
    response = client.post("/api/transform", json={"text": "AI", "include_debug": True})

    assert response.status_code == 200
    assert response.json()["normalized_text"] == "에이아이"
    assert "debug" in response.json()
    assert seen == ["AI"]


@pytest.mark.parametrize(
    "mode",
    ["span_default", "retired_mode", "unsupported_mode", "invalid"],
)
def test_phase25d_http_api_rejects_removed_rollout_field(mode: str) -> None:
    import api.server as server

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post(
        "/api/transform",
        json={"text": "90km/h", "rollout_mode": mode},
    )

    assert response.status_code == 422


def test_phase25d_direct_payload_rejects_removed_rollout_field(monkeypatch) -> None:
    import api.server as server

    def fail_if_called(*args, **kwargs):
        raise AssertionError("removed rollout field reached binary execution")

    monkeypatch.setattr(server, "run_transform_binary", fail_if_called)

    with pytest.raises(ValueError, match="not supported"):
        server.transform_request_payload(
            {"text": "90km/h", "rollout_mode": "span_default"}
        )


def test_phase25d_server_exposes_no_rollout_binary_helper() -> None:
    import api.server as server

    assert not hasattr(server, "run_transform_binary_with_rollout")


def test_phase25d_server_route_smoke_remains_pass(monkeypatch) -> None:
    import api.server as server

    monkeypatch.setattr(server, "run_transform_binary", lambda text: "__server-binary__")
    client = TestClient(server.app)
    response = client.post("/api/transform", json={"text": "서버 경로"})

    assert response.status_code == 200
    assert response.json() == {"normalized_text": "__server-binary__"}
