from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_phase25a_binary_runtime_current_legacy_helper_contract(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    def fake_run(cmd, *, input, capture_output, text, check):
        assert cmd == ["/tmp/fake-binary"]
        assert input == "입력 텍스트"
        assert capture_output is True
        assert text is True
        assert check is False
        return SimpleNamespace(returncode=0, stdout="정규화 결과\n", stderr="")

    monkeypatch.setattr(binary_runtime, "resolve_binary_path", lambda: Path("/tmp/fake-binary"))
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    output = binary_runtime.run_transform_binary("입력 텍스트")

    assert output == "정규화 결과"


def test_phase25a_binary_runtime_default_rollout_wrapper_current_contract(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    monkeypatch.setattr(binary_runtime, "run_transform_binary", lambda text, binary_path=None: "__binary__")

    assert binary_runtime.run_transform_binary_with_rollout("AI") == "__binary__"


def test_phase25a_server_route_still_uses_current_binary_path(monkeypatch) -> None:
    import api.server as server

    seen: list[str] = []

    def fake_run_transform_binary(text: str) -> str:
        seen.append(text)
        return "__server-binary__"

    def fail_if_rollout_used(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("rollout helper should not be used by the live route")

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)
    monkeypatch.setattr(server, "run_transform_binary_with_rollout", fail_if_rollout_used)

    result = server.transform_api(server.TransformRequest(text="서버 경로"))

    assert result == {"normalized_text": "__server-binary__"}
    assert seen == ["서버 경로"]

