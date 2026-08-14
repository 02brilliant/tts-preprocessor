from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BINARY_NAME = "tts_preprocessor"
DEFAULT_LLM_STAGE_BINARY_NAME = "tts-llm-stage"
# API production runtime resolves and executes packaged binaries instead of
# importing engine.* or LLM.* source modules from the deployed server filesystem.


class BinaryRuntimeError(RuntimeError):
    """Raised when the packaged runtime binary cannot be executed safely."""


class LLMStageRuntimeError(RuntimeError):
    """Raised when the packaged stage-2 binary returns a structured failure."""

    def __init__(self, message: str, *, status_code: int, detail: object) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


def _iter_binary_candidates() -> list[Path]:
    candidates: list[Path] = []

    env_path = os.getenv("TTS_PREPROCESSOR_BINARY")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    candidates.append(ROOT_DIR / "dist" / DEFAULT_BINARY_NAME)
    candidates.append(
        ROOT_DIR / "packages" / "tts-preprocessor" / "tts-preprocessor"
    )

    return candidates


def resolve_binary_path() -> Path:
    for candidate in _iter_binary_candidates():
        resolved = candidate if candidate.is_absolute() else (ROOT_DIR / candidate).resolve()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved

    searched = ", ".join(str(path) for path in _iter_binary_candidates()) or "<none>"
    raise FileNotFoundError(f"No executable runtime binary found. Searched: {searched}")


def _iter_llm_stage_binary_candidates() -> list[Path]:
    candidates: list[Path] = []

    env_path = os.getenv("TTS_LLM_STAGE_BINARY")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    try:
        stage_one = resolve_binary_path()
        candidates.append(stage_one.parent / DEFAULT_LLM_STAGE_BINARY_NAME)
    except FileNotFoundError:
        pass

    candidates.append(ROOT_DIR / "dist" / DEFAULT_LLM_STAGE_BINARY_NAME)
    candidates.append(
        ROOT_DIR / "packages" / "tts-preprocessor" / DEFAULT_LLM_STAGE_BINARY_NAME
    )
    return candidates


def resolve_llm_stage_binary_path() -> Path:
    for candidate in _iter_llm_stage_binary_candidates():
        resolved = candidate if candidate.is_absolute() else (ROOT_DIR / candidate).resolve()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved

    searched = (
        ", ".join(str(path) for path in _iter_llm_stage_binary_candidates()) or "<none>"
    )
    raise FileNotFoundError(
        f"No executable LLM stage binary found. Searched: {searched}"
    )


def run_transform_binary(text: str, *, binary_path: Path | None = None) -> str:
    """Run the packaged production binary through its single span contract."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    runtime_binary = binary_path or resolve_binary_path()
    return _run_binary_command([str(runtime_binary)], text=text)


def run_transform_binary_debug(
    text: str,
    *,
    binary_path: Path | None = None,
) -> dict:
    """Run the packaged production binary and return span debug JSON."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    runtime_binary = binary_path or resolve_binary_path()
    command = [str(runtime_binary), "--include-debug"]

    raw_output = _run_binary_command(command, text=text)

    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValueError("binary returned invalid debug JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("binary returned non-object debug payload")
    return payload


def _run_binary_command(command: list[str], *, text: str) -> str:
    result = subprocess.run(
        command,
        input=text,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "binary execution failed"
        raise BinaryRuntimeError(stderr)

    normalized = result.stdout.rstrip("\n")
    if not normalized:
        raise BinaryRuntimeError("binary returned empty output")
    return normalized


def list_llm_stage_models(*, binary_path: Path | None = None) -> dict:
    """Return model IDs packaged in the stage-2 binary."""

    runtime_binary = binary_path or resolve_llm_stage_binary_path()
    raw_output = _run_binary_command(
        [str(runtime_binary), "--list-models"],
        text="",
    )
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise BinaryRuntimeError("LLM stage binary returned invalid model JSON.") from exc
    if not isinstance(payload, dict):
        raise BinaryRuntimeError("LLM stage binary returned a non-object model list.")
    models = payload.get("models")
    default_model = payload.get("default_model")
    if (
        not isinstance(models, list)
        or not models
        or any(not isinstance(model, str) for model in models)
        or not isinstance(default_model, str)
        or default_model not in models
    ):
        raise BinaryRuntimeError("LLM stage binary returned an invalid model list.")
    return {"models": models, "default_model": default_model}


def run_llm_stage_binary(
    normalized_text: str,
    *,
    model: str | None = None,
    binary_path: Path | None = None,
) -> dict:
    """Run the packaged stage-2 binary and return the API JSON contract."""

    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be a string")
    if model is not None and not isinstance(model, str):
        raise TypeError("model must be str or None")

    runtime_binary = binary_path or resolve_llm_stage_binary_path()
    command = [str(runtime_binary), "--json"]
    if model is not None:
        command.extend(["--model", model])

    result = subprocess.run(
        command,
        input=normalized_text,
        capture_output=True,
        text=True,
        check=False,
    )
    raw_output = result.stdout.strip() or result.stderr.strip()
    payload = _parse_llm_stage_payload(raw_output)
    if result.returncode != 0 or payload.get("ok") is False:
        status_code = payload.get("status")
        detail = payload.get("detail")
        if not isinstance(status_code, int):
            status_code = 502
        if detail is None:
            detail = raw_output or "LLM stage binary execution failed."
        message = detail if isinstance(detail, str) else str(detail)
        raise LLMStageRuntimeError(message, status_code=status_code, detail=detail)

    speech_text = payload.get("speech_text")
    selected_model = payload.get("model")
    elapsed_ms = payload.get("elapsed_ms")
    if (
        not isinstance(speech_text, str)
        or not speech_text
        or not isinstance(selected_model, str)
        or not selected_model
        or not isinstance(elapsed_ms, (int, float))
    ):
        raise BinaryRuntimeError("LLM stage binary returned an invalid transform payload.")
    return {
        "speech_text": speech_text,
        "model": selected_model,
        "elapsed_ms": float(elapsed_ms),
    }


def _parse_llm_stage_payload(raw_output: str) -> dict:
    if not raw_output:
        raise BinaryRuntimeError("LLM stage binary returned empty output")
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise BinaryRuntimeError(raw_output) from exc
    if not isinstance(payload, dict):
        raise BinaryRuntimeError("LLM stage binary returned a non-object payload.")
    return payload
