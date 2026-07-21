from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_phase25a_binary_runtime_text_contract(monkeypatch) -> None:
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

    assert binary_runtime.run_transform_binary("입력 텍스트") == "정규화 결과"
