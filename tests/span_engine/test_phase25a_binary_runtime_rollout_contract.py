from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


def test_phase25a_binary_runtime_has_no_rollout_helper() -> None:
    import api.binary_runtime as binary_runtime

    assert not hasattr(binary_runtime, "run_transform_binary_with_rollout")


def test_phase25a_binary_runtime_debug_command_is_mode_less(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    seen: dict[str, object] = {}

    def fake_run(cmd, *, input, capture_output, text, check):
        seen["cmd"] = cmd
        seen["input"] = input
        seen["capture_output"] = capture_output
        seen["text"] = text
        seen["check"] = check
        return SimpleNamespace(
            returncode=0,
            stdout='{"ok": true, "normalized_text": "시속 구십 킬로미터"}\n',
            stderr="",
        )

    monkeypatch.setattr(binary_runtime, "resolve_binary_path", lambda: Path("/tmp/fake-binary"))
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    result = binary_runtime.run_transform_binary_debug("90km/h")

    assert seen["cmd"] == ["/tmp/fake-binary", "--include-debug"]
    assert seen["input"] == "90km/h"
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert seen["check"] is False
    assert result["ok"] is True
    assert result["normalized_text"] == "시속 구십 킬로미터"


def test_phase25a_old_binary_debug_fails_without_source_fallback(
    monkeypatch,
) -> None:
    import api.binary_runtime as binary_runtime

    real_import_module = binary_runtime.importlib.import_module

    def fail_import_engine_main(name: str):
        if name == "engine.main":
            raise AssertionError("production default must not import engine.main as fallback")
        return real_import_module(name)

    monkeypatch.delenv(binary_runtime.SOURCE_DEBUG_FALLBACK_ENV, raising=False)
    monkeypatch.setattr(binary_runtime, "resolve_binary_path", lambda: Path("/tmp/fake-binary"))
    monkeypatch.setattr(
        binary_runtime.subprocess,
        "run",
        lambda cmd, *, input, capture_output, text, check: SimpleNamespace(
            returncode=2,
            stdout="",
            stderr="unrecognized arguments: --include-debug",
        ),
    )
    monkeypatch.setattr(binary_runtime.importlib, "import_module", fail_import_engine_main)

    with pytest.raises(binary_runtime.BinaryRuntimeError) as excinfo:
        binary_runtime.run_transform_binary_debug("[3kg]")

    message = str(excinfo.value)
    assert "does not support debug output" in message
    assert "source debug fallback is disabled by default" in message
    assert "rebuild or update the packaged binary" in message


def test_phase25a_old_binary_source_debug_fallback_requires_opt_in(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    monkeypatch.setenv(binary_runtime.SOURCE_DEBUG_FALLBACK_ENV, "true")
    monkeypatch.setattr(binary_runtime, "resolve_binary_path", lambda: Path("/tmp/fake-binary"))
    monkeypatch.setattr(
        binary_runtime.subprocess,
        "run",
        lambda cmd, *, input, capture_output, text, check: SimpleNamespace(
            returncode=2,
            stdout="",
            stderr="unrecognized arguments: --include-debug",
        ),
    )

    result = binary_runtime.run_transform_binary_debug("[3kg]")

    assert result["ok"] is True
    assert result["normalized_text"] == "3kg"
    assert "debug" in result
