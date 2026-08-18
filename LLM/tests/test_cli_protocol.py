from __future__ import annotations

from argparse import Namespace
import json

from LLM.cli_protocol import classify_llm_stage_error
from LLM.config import ConfigurationError
from LLM.response_validation import LLMStageContractError
from LLM.stage_engine import UnsupportedLLMModelError
from LLM.vllm_client import VllmTimeoutError
from bin import build_llm_stage_entrypoint as entrypoint


def test_classify_unsupported_model() -> None:
    status, detail = classify_llm_stage_error(UnsupportedLLMModelError("Unsupported LLM model."))
    assert status == 400
    assert detail == "Unsupported LLM model."


def test_classify_missing_configuration() -> None:
    status, detail = classify_llm_stage_error(
        ConfigurationError("Required environment variable VLLM_BASE_URL is missing.")
    )
    assert status == 503
    assert "VLLM_BASE_URL" in detail


def test_classify_contract_violation() -> None:
    status, detail = classify_llm_stage_error(
        LLMStageContractError(
            "LLM response changed a stage-1 confirmed news reading.",
            stage="speech",
            output_text="오늘 뉴스 보도입니다.",
        )
    )
    assert status == 502
    assert detail == {
        "message": "LLM response changed a stage-1 confirmed news reading.",
        "stage": "speech",
        "speech_text": "오늘 뉴스 보도입니다.",
    }


def test_classify_timeout() -> None:
    status, detail = classify_llm_stage_error(
        VllmTimeoutError("vLLM server request timed out.")
    )
    assert status == 504
    assert detail == "vLLM server request timed out."


def test_entrypoint_list_models_prints_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda: Namespace(
            input=None,
            output=None,
            text=None,
            model=None,
            json=False,
            list_models=True,
            check=False,
        ),
    )

    assert entrypoint.run() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["default_model"] == "gemma4-31B-it (vLLM)"
    assert "gemma4-31B-it (vLLM)" in payload["models"]


def test_entrypoint_json_success(monkeypatch, capsys) -> None:
    class FakeResult:
        speech_text = "궁무른, 조씀니다."
        model = "gemma4:e4b"
        elapsed_ms = 12.3456

    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda: Namespace(
            input=None,
            output=None,
            text="국물은 좋습니다.",
            model="gemma4:e4b",
            json=True,
            list_models=False,
            check=False,
        ),
    )
    monkeypatch.setattr(
        "LLM.stage_engine.transform",
        lambda normalized_text, model=None: FakeResult(),
    )

    assert entrypoint.run() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "speech_text": "궁무른, 조씀니다.",
        "model": "gemma4:e4b",
        "elapsed_ms": 12.346,
    }


def test_entrypoint_json_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda: Namespace(
            input=None,
            output=None,
            text="원고",
            model="unknown",
            json=True,
            list_models=False,
            check=False,
        ),
    )
    monkeypatch.setattr(
        "LLM.stage_engine.transform",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            UnsupportedLLMModelError("Unsupported LLM model.")
        ),
    )

    assert entrypoint.run() == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload == {
        "ok": False,
        "status": 400,
        "detail": "Unsupported LLM model.",
    }
