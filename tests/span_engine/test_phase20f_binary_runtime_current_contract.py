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


def test_phase20f_binary_runtime_runs_llm_stage_json_contract(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime
    import json

    seen: dict[str, object] = {}

    def fake_run(cmd, *, input, capture_output, text, check):
        seen["cmd"] = cmd
        seen["input"] = input
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "speech_text": "궁무른, 조씀니다.",
                    "model": "gemma4:e4b",
                    "elapsed_ms": 12.5,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(
        binary_runtime,
        "resolve_llm_stage_binary_path",
        lambda: Path("/tmp/fake-llm-stage"),
    )
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    result = binary_runtime.run_llm_stage_binary(
        "국물은 좋습니다.",
        model="gemma4:e4b",
    )

    assert result == {
        "speech_text": "궁무른, 조씀니다.",
        "model": "gemma4:e4b",
        "elapsed_ms": 12.5,
    }
    assert seen["cmd"] == ["/tmp/fake-llm-stage", "--json", "--model", "gemma4:e4b"]
    assert seen["input"] == "국물은 좋습니다."


def test_phase20f_binary_runtime_maps_llm_stage_json_error(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime
    import json

    def fake_run(cmd, *, input, capture_output, text, check):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr=json.dumps(
                {
                    "ok": False,
                    "status": 503,
                    "detail": "Required environment variable VLLM_BASE_URL is missing.",
                }
            ),
        )

    monkeypatch.setattr(
        binary_runtime,
        "resolve_llm_stage_binary_path",
        lambda: Path("/tmp/fake-llm-stage"),
    )
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    try:
        binary_runtime.run_llm_stage_binary("원고", model="gemma4-31B-it (vLLM)")
    except binary_runtime.LLMStageRuntimeError as exc:
        assert exc.status_code == 503
        assert "VLLM_BASE_URL" in str(exc.detail)
    else:
        raise AssertionError("expected LLMStageRuntimeError")
