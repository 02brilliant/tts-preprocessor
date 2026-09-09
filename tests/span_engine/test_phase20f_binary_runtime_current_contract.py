from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


def test_phase20f_binary_runtime_run_transform_binary_exists() -> None:
    import api.binary_runtime as binary_runtime

    assert callable(binary_runtime.run_transform_binary)


def test_phase20f_binary_runtime_run_transform_binary_uses_subprocess_result(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    seen: dict[str, object] = {}

    def fake_run(cmd, *, input, capture_output, text, check, timeout=None):
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


def test_phase20f_binary_runtime_selects_simplified_binary(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    seen: dict[str, object] = {}

    def fake_run(cmd, *, input, capture_output, text, check, timeout=None):
        seen["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="간소화 결과\n", stderr="")

    monkeypatch.setattr(
        binary_runtime,
        "resolve_simplified_binary_path",
        lambda: Path("/tmp/fake-simplified-binary"),
    )
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    assert binary_runtime.run_transform_binary(
        "입력 텍스트",
        profile="simplified",
    ) == "간소화 결과"
    assert seen["cmd"] == ["/tmp/fake-simplified-binary"]


def test_phase20f_binary_runtime_runs_integrated_json_contract(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime
    import json

    seen: dict[str, object] = {}

    def fake_run(cmd, *, input, capture_output, text, check, timeout=None):
        seen["cmd"] = cmd
        seen["input"] = input
        seen["timeout"] = timeout
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "normalized_text": "국물은 좋습니다.",
                    "speech_text": "궁무른, 조씀니다.",
                    "model": "gemma4:e4b",
                    "elapsed_ms": 12.5,
                    "rule_elapsed_ms": 4.0,
                    "llm_elapsed_ms": 13.0,
                    "llm_called": True,
                    "llm_skip_reason": None,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(
        binary_runtime,
        "resolve_integrated_binary_path",
        lambda level: Path(f"/tmp/fake-level-{level}"),
    )
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    result = binary_runtime.run_integrated_binary(
        "원문",
        level=4,
        model="gemma4:e4b",
    )

    assert result == {
        "normalized_text": "국물은 좋습니다.",
        "speech_text": "궁무른, 조씀니다.",
        "model": "gemma4:e4b",
        "elapsed_ms": 12.5,
        "rule_elapsed_ms": 4.0,
        "llm_elapsed_ms": 13.0,
        "llm_called": True,
        "llm_skip_reason": None,
        "llm_status": "applied",
        "fallback_used": False,
        "fallback_reason": None,
    }
    assert seen["cmd"] == [
        "/tmp/fake-level-4",
        "--json",
        "--model",
        "gemma4:e4b",
    ]
    assert seen["input"] == "원문"
    assert seen["timeout"] == 20.0


@pytest.mark.parametrize("level", (4, 5))
def test_phase20f_natural_level_forwards_only_structured_fallback_log(
    monkeypatch,
    caplog,
    level: int,
) -> None:
    import api.binary_runtime as binary_runtime
    import json

    def fake_run(cmd, *, input, capture_output, text, check, timeout=None):
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "normalized_text": "보호된 원고",
                    "speech_text": "보호된 원고",
                    "model": "gemma4-31B-it (vLLM)",
                    "elapsed_ms": 1.0,
                    "rule_elapsed_ms": 1.0,
                    "llm_elapsed_ms": 2.0,
                    "llm_called": True,
                    "llm_skip_reason": None,
                }
            ),
            stderr=(
                f"level{level}_validation_fallback code=PROTECTED_SPAN_MUTATION "
                "severity=Critical\n원문은 기록하지 않는다"
            ),
        )

    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)
    caplog.set_level("WARNING")

    result = binary_runtime.run_integrated_binary(
        "비공개 원문",
        level=level,
        binary_path=Path(f"/tmp/fake-level-{level}"),
    )

    assert result["speech_text"] == "보호된 원고"
    assert "PROTECTED_SPAN_MUTATION" in caplog.text
    assert "비공개 원문" not in caplog.text
    assert "원문은 기록하지 않는다" not in caplog.text


def test_phase20f_level4_drops_rejected_output_from_public_contract(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime
    import json

    def fake_run(cmd, *, input, capture_output, text, check, timeout=None):
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "normalized_text": "가격은 삼-쩜-영오 달러입니다.",
                    "speech_text": "가격은 삼-쩜-영오 달러입니다.",
                    "model": "gemma4-31B-it (vLLM)",
                    "elapsed_ms": 1.0,
                    "rule_elapsed_ms": 1.0,
                    "llm_elapsed_ms": 2.0,
                    "llm_called": True,
                    "llm_skip_reason": None,
                    "rejected_speech_text": "<SPEECH_TEXT>가격은 삼점영오 달러입니다.</SPEECH_TEXT>",
                    "validation_failure": {
                        "code": "LOCKED_READING_MUTATION",
                        "severity": "Critical",
                        "message": "LLM response changed a rule-engine locked reading.",
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    result = binary_runtime.run_integrated_binary(
        "가격은 3.05달러입니다.",
        level=4,
        binary_path=Path("/tmp/fake-level-4"),
    )

    assert result["speech_text"] == "가격은 삼-쩜-영오 달러입니다."
    assert "rejected_speech_text" not in result
    assert "<SPEECH_TEXT>" not in str(result)
    assert result["validation_failure"]["code"] == "LOCKED_READING_MUTATION"


def test_phase20f_integrated_process_timeout_uses_rules_only_fallback(
    monkeypatch,
) -> None:
    import api.binary_runtime as binary_runtime
    import json

    calls = []

    def fake_run(cmd, *, input, capture_output, text, check, timeout=None):
        calls.append((cmd, timeout))
        if len(calls) == 1:
            raise binary_runtime.subprocess.TimeoutExpired(cmd, timeout)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "normalized_text": "규칙 결과",
                    "speech_text": "오단계 확정 결과",
                    "model": "gemma4:e4b",
                    "elapsed_ms": 0.0,
                    "rule_elapsed_ms": 2.0,
                    "llm_elapsed_ms": 0.0,
                    "llm_called": False,
                    "llm_skip_reason": "rules_only_requested",
                    "llm_status": "rules_only",
                    "fallback_used": True,
                    "fallback_reason": "RULES_ONLY_REQUESTED",
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)
    result = binary_runtime.run_integrated_binary(
        "원고",
        level=5,
        model="gemma4:e4b",
        binary_path=Path("/tmp/fake-level-5"),
    )

    assert calls == [
        (["/tmp/fake-level-5", "--json", "--model", "gemma4:e4b"], 20.0),
        (
            [
                "/tmp/fake-level-5",
                "--json",
                "--rules-only",
                "--model",
                "gemma4:e4b",
            ],
            5.0,
        ),
    ]
    assert result["speech_text"] == "오단계 확정 결과"
    assert result["llm_called"] is True
    assert result["llm_status"] == "process_timeout"
    assert result["fallback_used"] is True
    assert result["fallback_reason"] == "INTEGRATED_PROCESS_TIMEOUT"


def test_phase20f_explicit_rules_only_uses_short_deadline(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime
    import json

    seen = {}

    def fake_run(cmd, *, input, capture_output, text, check, timeout=None):
        seen.update({"cmd": cmd, "timeout": timeout})
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "normalized_text": "규칙 결과",
                    "speech_text": "오단계 확정 결과",
                    "model": "gemma4:e4b",
                    "elapsed_ms": 0.0,
                    "rule_elapsed_ms": 2.0,
                    "llm_elapsed_ms": 0.0,
                    "llm_called": False,
                    "llm_skip_reason": "rules_only_requested",
                    "llm_status": "rules_only",
                    "fallback_used": True,
                    "fallback_reason": "RULES_ONLY_REQUESTED",
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)
    result = binary_runtime.run_integrated_binary(
        "원고",
        level=5,
        model="gemma4:e4b",
        binary_path=Path("/tmp/fake-level-5"),
        rules_only=True,
    )

    assert seen == {
        "cmd": [
            "/tmp/fake-level-5",
            "--json",
            "--rules-only",
            "--model",
            "gemma4:e4b",
        ],
        "timeout": 5.0,
    }
    assert result["speech_text"] == "오단계 확정 결과"
    assert result["llm_called"] is False


@pytest.mark.parametrize("raw", ("0", "nan", "not-a-number"))
def test_phase20f_integrated_rejects_invalid_process_timeout(
    monkeypatch,
    raw: str,
) -> None:
    import api.binary_runtime as binary_runtime

    monkeypatch.setenv("TTS_PREPROCESSOR_LLM_PROCESS_TIMEOUT_SECONDS", raw)
    with pytest.raises(binary_runtime.BinaryRuntimeError, match="TIMEOUT_SECONDS"):
        binary_runtime.run_integrated_binary(
            "원고",
            level=5,
            binary_path=Path("/tmp/fake-level-5"),
        )


def test_phase20f_invalid_binary_output_does_not_expose_raw_tags(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime

    def fake_run(cmd, *, input, capture_output, text, check, timeout=None):
        return SimpleNamespace(
            returncode=0,
            stdout="<SPEECH_TEXT>모델 원출력</SPEECH_TEXT>",
            stderr="",
        )

    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)
    with pytest.raises(binary_runtime.BinaryRuntimeError) as raised:
        binary_runtime.run_integrated_binary(
            "원고",
            level=5,
            binary_path=Path("/tmp/fake-level-5"),
        )

    assert str(raised.value) == "Integrated LLM binary returned invalid JSON."
    assert "SPEECH_TEXT" not in str(raised.value)
    assert "모델 원출력" not in str(raised.value)


def test_phase20f_binary_runtime_maps_integrated_json_error(monkeypatch) -> None:
    import api.binary_runtime as binary_runtime
    import json

    def fake_run(cmd, *, input, capture_output, text, check, timeout=None):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr=json.dumps(
                {
                    "ok": False,
                    "status": 503,
                    "detail": "Required environment variable VLLM_BASE_URL is missing.",
                    "normalized_text": "규칙 결과",
                }
            ),
        )

    monkeypatch.setattr(
        binary_runtime,
        "resolve_integrated_binary_path",
        lambda level: Path(f"/tmp/fake-level-{level}"),
    )
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    try:
        binary_runtime.run_integrated_binary("원고", level=3, model="gemma4-31B-it (vLLM)")
    except binary_runtime.LLMStageRuntimeError as exc:
        assert exc.status_code == 503
        assert "VLLM_BASE_URL" in str(exc.detail)
    else:
        raise AssertionError("expected LLMStageRuntimeError")
