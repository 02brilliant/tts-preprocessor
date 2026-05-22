from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


def test_phase25a_binary_runtime_invalid_rollout_mode_rejected() -> None:
    from api.binary_runtime import run_transform_binary_with_rollout

    with pytest.raises(ValueError):
        run_transform_binary_with_rollout("AI", rollout_mode="not-a-mode")


def test_phase25a_binary_runtime_future_rollout_command_includes_rollout_flags(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    seen: dict[str, object] = {}

    def fake_run(cmd, *, input, capture_output, text, check):
        seen["cmd"] = cmd
        seen["input"] = input
        seen["capture_output"] = capture_output
        seen["text"] = text
        seen["check"] = check
        return SimpleNamespace(returncode=0, stdout='{"ok": true, "mode": "span_default"}\n', stderr="")

    monkeypatch.setattr(binary_runtime, "resolve_binary_path", lambda: Path("/tmp/fake-binary"))
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    result = binary_runtime.run_transform_binary_with_rollout(
        "90km/h",
        rollout_mode="span_default",
        include_debug=True,
    )

    assert seen["cmd"] == [
        "/tmp/fake-binary",
        "--rollout-mode",
        "span_default",
        "--include-debug",
    ]
    assert seen["input"] == "90km/h"
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert seen["check"] is False
    assert result["mode"] == "span_default"
    assert result["ok"] is True


@pytest.mark.parametrize(
    "stderr",
    [
        "unrecognized arguments: --rollout-mode span_shadow_compare",
        "unrecognized arguments: --include-debug",
    ],
)
def test_phase25a_binary_runtime_old_binary_rollout_args_fail_without_source_fallback(
    monkeypatch,
    stderr: str,
) -> None:
    import api.binary_runtime as binary_runtime

    real_import_module = binary_runtime.importlib.import_module

    def fail_import_engine_main(name: str):
        if name == "engine.main":
            raise AssertionError("production default must not import engine.main as fallback")
        return real_import_module(name)

    monkeypatch.delenv(binary_runtime.SOURCE_ROLLOUT_FALLBACK_ENV, raising=False)
    monkeypatch.setattr(binary_runtime, "resolve_binary_path", lambda: Path("/tmp/fake-binary"))
    monkeypatch.setattr(
        binary_runtime.subprocess,
        "run",
        lambda cmd, *, input, capture_output, text, check: SimpleNamespace(
            returncode=2,
            stdout="",
            stderr=stderr,
        ),
    )
    monkeypatch.setattr(binary_runtime.importlib, "import_module", fail_import_engine_main)

    with pytest.raises(binary_runtime.BinaryRuntimeError) as excinfo:
        binary_runtime.run_transform_binary_with_rollout(
            "[3kg]",
            rollout_mode="span_shadow_compare",
            include_debug=True,
        )

    message = str(excinfo.value)
    assert "does not support rollout/debug arguments" in message
    assert "source rollout fallback is disabled by default for production runtime" in message
    assert "rebuild or update the packaged binary" in message
    assert stderr in message


def test_phase25a_binary_runtime_old_binary_rollout_source_fallback_requires_opt_in(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    monkeypatch.setenv(binary_runtime.SOURCE_ROLLOUT_FALLBACK_ENV, "true")
    monkeypatch.setattr(binary_runtime, "resolve_binary_path", lambda: Path("/tmp/fake-binary"))
    monkeypatch.setattr(
        binary_runtime.subprocess,
        "run",
        lambda cmd, *, input, capture_output, text, check: SimpleNamespace(
            returncode=2,
            stdout="",
            stderr="unrecognized arguments: --rollout-mode span_shadow_compare --include-debug",
        ),
    )

    result = binary_runtime.run_transform_binary_with_rollout(
        "[3kg]",
        rollout_mode="span_shadow_compare",
        include_debug=True,
    )

    assert result["mode"] == "span_shadow_compare"
    assert result["legacy_output"] == "삼 킬로그램"
    assert result["span_output"] == "3kg"
    assert result["compare"]["category"] == "intended_v5_change"
