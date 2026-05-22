from __future__ import annotations


def test_phase20g_server_imports_and_exposes_transform_route() -> None:
    import api.server as server

    assert server.app is not None
    assert callable(server.transform_api)


def test_phase20g_server_transform_route_uses_binary_runtime_path(monkeypatch) -> None:
    import api.server as server

    seen: list[str] = []

    def fake_run_transform_binary(text: str) -> str:
        seen.append(text)
        return "__server-binary__"

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)

    result = server.transform_api(server.TransformRequest(text="서버 경로"))

    assert result == {"normalized_text": "__server-binary__"}
    assert seen == ["서버 경로"]
