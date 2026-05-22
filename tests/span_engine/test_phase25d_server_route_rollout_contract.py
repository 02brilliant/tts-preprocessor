from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_phase25d_default_request_remains_legacy_route(monkeypatch) -> None:
    import api.server as server

    seen: list[str] = []

    def fake_run_transform_binary(text: str) -> str:
        seen.append(text)
        return "에이아이"

    def fail_if_rollout_used(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("rollout helper should not be used for plain requests")

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)
    monkeypatch.setattr(server, "run_transform_binary_with_rollout", fail_if_rollout_used)

    client = TestClient(server.app)
    response = client.post("/api/transform", json={"text": "AI"})

    assert response.status_code == 200
    assert response.json() == {"normalized_text": "에이아이"}
    assert seen == ["AI"]


def test_phase25d_include_debug_without_rollout_mode_stays_current_behavior(monkeypatch) -> None:
    import api.server as server

    monkeypatch.setattr(server, "run_transform_binary", lambda text: "에이아이")
    client = TestClient(server.app)
    response = client.post("/api/transform", json={"text": "AI", "include_debug": True})

    assert response.status_code == 200
    assert response.json() == {"normalized_text": "에이아이"}


def test_phase25d_explicit_span_default_should_route_through_rollout_helper(monkeypatch) -> None:
    import api.server as server

    seen: dict[str, object] = {}

    def fake_run_transform_binary(text: str) -> str:
        seen["legacy_called"] = text
        return "삼 킬로그램"

    def fake_run_transform_binary_with_rollout(text: str, rollout_mode="legacy_default", include_debug=False):
        seen["rollout_called"] = {
            "text": text,
            "rollout_mode": rollout_mode,
            "include_debug": include_debug,
        }
        return {"ok": True, "mode": rollout_mode, "normalized_text": "3kg"}

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)
    monkeypatch.setattr(server, "run_transform_binary_with_rollout", fake_run_transform_binary_with_rollout)

    client = TestClient(server.app)
    response = client.post("/api/transform", json={"text": "[3kg]", "rollout_mode": "span_default"})

    assert response.status_code == 200
    assert response.json()["normalized_text"] == "3kg"
    assert seen["rollout_called"]["rollout_mode"] == "span_default"
    assert "legacy_called" not in seen


def test_phase25d_explicit_shadow_debug_should_return_structured_payload(monkeypatch) -> None:
    import api.server as server

    def fake_run_transform_binary(text: str) -> str:
        return "시속 구십 킬로미터"

    def fake_run_transform_binary_with_rollout(text: str, rollout_mode="legacy_default", include_debug=False):
        return {
            "ok": True,
            "mode": rollout_mode,
            "normalized_text": "시속 구십 킬로미터",
            "production_output": "시속 구십 킬로미터",
            "legacy_output": "시속 구십 킬로미터",
            "span_output": "시속 구십 킬로미터",
            "compare": {"category": "same"},
        }

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)
    monkeypatch.setattr(server, "run_transform_binary_with_rollout", fake_run_transform_binary_with_rollout)

    client = TestClient(server.app)
    response = client.post(
        "/api/transform",
        json={"text": "90km/h", "rollout_mode": "span_shadow_compare", "include_debug": True},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == "span_shadow_compare"
    assert result["compare"]["category"] == "same"


def test_phase25d_invalid_rollout_mode_should_not_silently_fall_back(monkeypatch) -> None:
    import api.server as server

    def fake_run_transform_binary(text: str) -> str:
        return "에이아이"

    def fake_run_transform_binary_with_rollout(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise ValueError("invalid rollout mode")

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)
    monkeypatch.setattr(server, "run_transform_binary_with_rollout", fake_run_transform_binary_with_rollout)

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/transform", json={"text": "AI", "rollout_mode": "invalid"})

    assert response.status_code == 400
    assert "invalid rollout mode" in response.text


def test_phase25d_rollout_helper_only_called_when_rollout_mode_exists(monkeypatch) -> None:
    import api.server as server

    seen: list[str] = []

    def fake_run_transform_binary(text: str) -> str:
        seen.append("legacy")
        return "에이아이"

    def fake_run_transform_binary_with_rollout(*args, **kwargs):  # type: ignore[no-untyped-def]
        seen.append("rollout")
        return {"ok": True, "mode": "span_default", "normalized_text": "에이아이"}

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)
    monkeypatch.setattr(server, "run_transform_binary_with_rollout", fake_run_transform_binary_with_rollout)

    client = TestClient(server.app)
    client.post("/api/transform", json={"text": "AI"})
    assert seen == ["legacy"]


def test_phase25d_server_route_smoke_remains_pass(monkeypatch) -> None:
    import api.server as server

    monkeypatch.setattr(server, "run_transform_binary", lambda text: "__server-binary__")
    client = TestClient(server.app)
    response = client.post("/api/transform", json={"text": "서버 경로"})

    assert response.status_code == 200
    assert response.json() == {"normalized_text": "__server-binary__"}
