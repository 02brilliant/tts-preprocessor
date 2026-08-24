from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BINARY_NAME = "tts_preprocessor"
DEFAULT_SIMPLIFIED_BINARY_NAME = "tts-preprocessor-simplified"
DEFAULT_LLM_MINIMAL_BINARY_NAME = "tts-preprocessor-llm-minimal"
DEFAULT_LLM_NATURAL_BINARY_NAME = "tts-preprocessor-llm-natural"
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


def _iter_simplified_binary_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.getenv("TTS_PREPROCESSOR_SIMPLIFIED_BINARY")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    try:
        default_binary = resolve_binary_path()
        candidates.append(default_binary.parent / DEFAULT_SIMPLIFIED_BINARY_NAME)
    except FileNotFoundError:
        pass
    candidates.append(ROOT_DIR / "dist" / DEFAULT_SIMPLIFIED_BINARY_NAME)
    candidates.append(
        ROOT_DIR / "packages" / "tts-preprocessor" / DEFAULT_SIMPLIFIED_BINARY_NAME
    )
    return candidates


def resolve_simplified_binary_path() -> Path:
    for candidate in _iter_simplified_binary_candidates():
        resolved = candidate if candidate.is_absolute() else (ROOT_DIR / candidate).resolve()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved
    searched = ", ".join(str(path) for path in _iter_simplified_binary_candidates())
    raise FileNotFoundError(
        f"No executable simplified runtime binary found. Searched: {searched}"
    )


def _integrated_binary_name(level: int) -> str:
    if level == 3:
        return DEFAULT_LLM_MINIMAL_BINARY_NAME
    if level == 4:
        return DEFAULT_LLM_NATURAL_BINARY_NAME
    raise ValueError("integrated LLM level must be 3 or 4")


def _iter_integrated_binary_candidates(level: int) -> list[Path]:
    candidates: list[Path] = []
    env_name = (
        "TTS_PREPROCESSOR_LLM_MINIMAL_BINARY"
        if level == 3
        else "TTS_PREPROCESSOR_LLM_NATURAL_BINARY"
    )
    env_path = os.getenv(env_name)
    if env_path:
        candidates.append(Path(env_path).expanduser())
    binary_name = _integrated_binary_name(level)
    try:
        rule_binary = resolve_binary_path()
        candidates.append(rule_binary.parent / binary_name)
    except FileNotFoundError:
        pass
    candidates.append(ROOT_DIR / "dist" / binary_name)
    candidates.append(
        ROOT_DIR / "packages" / "tts-preprocessor" / binary_name
    )
    return candidates


def resolve_integrated_binary_path(level: int) -> Path:
    for candidate in _iter_integrated_binary_candidates(level):
        resolved = candidate if candidate.is_absolute() else (ROOT_DIR / candidate).resolve()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved
    searched = ", ".join(str(path) for path in _iter_integrated_binary_candidates(level))
    raise FileNotFoundError(
        f"No executable integrated level-{level} binary found. Searched: {searched}"
    )


def run_transform_binary(
    text: str,
    *,
    profile: str = "default",
    binary_path: Path | None = None,
) -> str:
    """Run the packaged production binary through its single span contract."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if profile not in {"default", "simplified"}:
        raise ValueError("profile must be 'default' or 'simplified'")
    runtime_binary = binary_path or (
        resolve_simplified_binary_path()
        if profile == "simplified"
        else resolve_binary_path()
    )
    return _run_binary_command([str(runtime_binary)], text=text)


def run_transform_binary_debug(
    text: str,
    *,
    profile: str = "default",
    binary_path: Path | None = None,
) -> dict:
    """Run the packaged production binary and return span debug JSON."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if profile not in {"default", "simplified"}:
        raise ValueError("profile must be 'default' or 'simplified'")
    runtime_binary = binary_path or (
        resolve_simplified_binary_path()
        if profile == "simplified"
        else resolve_binary_path()
    )
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


def list_llm_models(*, binary_path: Path | None = None) -> dict:
    """Return model IDs packaged in the integrated level-3 binary."""

    runtime_binary = binary_path or resolve_integrated_binary_path(3)
    raw_output = _run_binary_command(
        [str(runtime_binary), "--list-models"],
        text="",
    )
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise BinaryRuntimeError("Integrated LLM binary returned invalid model JSON.") from exc
    if not isinstance(payload, dict):
        raise BinaryRuntimeError("Integrated LLM binary returned a non-object model list.")
    models = payload.get("models")
    default_model = payload.get("default_model")
    if (
        not isinstance(models, list)
        or not models
        or any(not isinstance(model, str) for model in models)
        or not isinstance(default_model, str)
        or default_model not in models
    ):
        raise BinaryRuntimeError("Integrated LLM binary returned an invalid model list.")
    return {"models": models, "default_model": default_model}


def run_integrated_binary(
    text: str,
    *,
    level: int,
    model: str | None = None,
    binary_path: Path | None = None,
) -> dict:
    """Run one packaged level-3/4 binary from original text to final speech."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if model is not None and not isinstance(model, str):
        raise TypeError("model must be str or None")
    if isinstance(level, bool) or level not in {3, 4}:
        raise ValueError("level must be 3 or 4")

    runtime_binary = binary_path or resolve_integrated_binary_path(level)
    command = [str(runtime_binary), "--json"]
    if model is not None:
        command.extend(["--model", model])

    result = subprocess.run(
        command,
        input=text,
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
            detail = raw_output or f"Integrated level-{level} binary execution failed."
        normalized_text = payload.get("normalized_text")
        if isinstance(detail, dict) and isinstance(normalized_text, str):
            detail = {**detail, "normalized_text": normalized_text}
        message = detail if isinstance(detail, str) else str(detail)
        raise LLMStageRuntimeError(message, status_code=status_code, detail=detail)

    speech_text = payload.get("speech_text")
    normalized_text = payload.get("normalized_text")
    selected_model = payload.get("model")
    elapsed_ms = payload.get("elapsed_ms")
    rule_elapsed_ms = payload.get("rule_elapsed_ms")
    llm_elapsed_ms = payload.get("llm_elapsed_ms")
    llm_called = payload.get("llm_called")
    llm_skip_reason = payload.get("llm_skip_reason")
    if (
        not isinstance(normalized_text, str)
        or not normalized_text
        or not isinstance(speech_text, str)
        or not speech_text
        or not isinstance(selected_model, str)
        or not selected_model
        or not isinstance(elapsed_ms, (int, float))
        or not isinstance(rule_elapsed_ms, (int, float))
        or not isinstance(llm_elapsed_ms, (int, float))
        or rule_elapsed_ms < 0
        or llm_elapsed_ms < 0
        or not isinstance(llm_called, bool)
        or (not llm_called and (elapsed_ms != 0 or llm_elapsed_ms != 0))
        or (not llm_called and not isinstance(llm_skip_reason, str))
        or (llm_called and llm_skip_reason is not None)
    ):
        raise BinaryRuntimeError("Integrated LLM binary returned an invalid transform payload.")
    return {
        "normalized_text": normalized_text,
        "speech_text": speech_text,
        "model": selected_model,
        "elapsed_ms": float(elapsed_ms),
        "rule_elapsed_ms": float(rule_elapsed_ms),
        "llm_elapsed_ms": float(llm_elapsed_ms),
        "llm_called": llm_called,
        "llm_skip_reason": llm_skip_reason,
    }


def _parse_llm_stage_payload(raw_output: str) -> dict:
    if not raw_output:
        raise BinaryRuntimeError("Integrated LLM binary returned empty output")
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise BinaryRuntimeError(raw_output) from exc
    if not isinstance(payload, dict):
        raise BinaryRuntimeError("LLM stage binary returned a non-object payload.")
    return payload
