from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_phase20f_binary_runtime_run_transform_binary_exists() -> None:
    import api.binary_runtime as binary_runtime

    assert callable(binary_runtime.run_transform_binary)


def test_phase20f_binary_runtime_run_transform_binary_uses_subprocess_result(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    seen: dict[str, object] = {}

    def fake_run(cmd, *, input, capture_output, text, check):
        seen["cmd"] = cmd
        seen["input"] = input
        seen["capture_output"] = capture_output
        seen["text"] = text
        seen["check"] = check
        return SimpleNamespace(returncode=0, stdout="정규화 결과\n", stderr="")

    monkeypatch.setattr(binary_runtime, "resolve_binary_path", lambda: Path("/tmp/fake-binary"))
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    output = binary_runtime.run_transform_binary("입력 텍스트")

    assert output == "정규화 결과"
    assert seen["cmd"] == ["/tmp/fake-binary"]
    assert seen["input"] == "입력 텍스트"
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert seen["check"] is False
