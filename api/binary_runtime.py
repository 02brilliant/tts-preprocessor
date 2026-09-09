from __future__ import annotations

import json
import logging
import math
import os
import re
import subprocess
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BINARY_NAME = "tts_preprocessor"
DEFAULT_SIMPLIFIED_BINARY_NAME = "tts-preprocessor-simplified"
DEFAULT_LLM_MINIMAL_BINARY_NAME = "tts-preprocessor-llm-minimal"
DEFAULT_LLM_NATURAL_BINARY_NAME = "tts-preprocessor-llm-natural"
DEFAULT_LLM_STANDARD_BINARY_NAME = "tts-preprocessor-llm-standard"
_LOGGER = logging.getLogger(__name__)
_FALLBACK_LOG_RE = re.compile(
    r"level(?P<level>[45])_validation_fallback code=(?P<code>[A-Z0-9_]+) "
    r"severity=(?P<severity>Critical|High)"
)
_LLM_STATUSES = frozenset(
    {
        "applied",
        "partial",
        "invalid_response",
        "timeout",
        "unavailable",
        "skipped",
        "rules_only",
        "process_timeout",
        "circuit_open",
        "overloaded",
    }
)
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
    if level == 5:
        return DEFAULT_LLM_STANDARD_BINARY_NAME
    raise ValueError("integrated LLM level must be 3, 4, or 5")


def _iter_integrated_binary_candidates(level: int) -> list[Path]:
    candidates: list[Path] = []
    env_name = {
        3: "TTS_PREPROCESSOR_LLM_MINIMAL_BINARY",
        4: "TTS_PREPROCESSOR_LLM_NATURAL_BINARY",
        5: "TTS_PREPROCESSOR_LLM_STANDARD_BINARY",
    }.get(level)
    if env_name is None:
        raise ValueError("integrated LLM level must be 3, 4, or 5")
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
    rules_only: bool = False,
) -> dict:
    """Run one packaged level-3/4/5 binary from original text to final speech."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if model is not None and not isinstance(model, str):
        raise TypeError("model must be str or None")
    if isinstance(level, bool) or level not in {3, 4, 5}:
        raise ValueError("level must be 3, 4, or 5")
    if not isinstance(rules_only, bool):
        raise TypeError("rules_only must be bool")

    runtime_binary = binary_path or resolve_integrated_binary_path(level)
    command = (
        _rules_only_command(runtime_binary, model=model)
        if rules_only
        else [str(runtime_binary), "--json"]
    )
    if model is not None and not rules_only:
        command.extend(["--model", model])

    process_timeout = _positive_timeout_env(
        "TTS_PREPROCESSOR_RULES_ONLY_TIMEOUT_SECONDS"
        if rules_only
        else "TTS_PREPROCESSOR_LLM_PROCESS_TIMEOUT_SECONDS",
        5.0 if rules_only else 20.0,
    )
    started_at = time.perf_counter()
    forced_fallback = False
    try:
        result = subprocess.run(
            command,
            input=text,
            capture_output=True,
            text=True,
            check=False,
            timeout=process_timeout,
        )
    except subprocess.TimeoutExpired as initial_timeout:
        if rules_only:
            raise BinaryRuntimeError(
                "Integrated rules-only runtime timed out."
            ) from initial_timeout
        forced_fallback = True
        fallback_command = _rules_only_command(runtime_binary, model=model)
        try:
            result = subprocess.run(
                fallback_command,
                input=text,
                capture_output=True,
                text=True,
                check=False,
                timeout=_positive_timeout_env(
                    "TTS_PREPROCESSOR_RULES_ONLY_TIMEOUT_SECONDS",
                    5.0,
                ),
            )
        except subprocess.TimeoutExpired as exc:
            raise BinaryRuntimeError(
                "Integrated runtime and its rules-only fallback both timed out."
            ) from exc
    raw_output = result.stdout.strip() or result.stderr.strip()
    if level in {4, 5}:
        _log_validation_fallback(result.stderr)
    payload = _parse_llm_stage_payload(raw_output)
    if forced_fallback and result.returncode == 0 and payload.get("ok") is not False:
        fallback_elapsed_ms = (time.perf_counter() - started_at) * 1000
        payload.update(
            {
                "elapsed_ms": fallback_elapsed_ms,
                "llm_elapsed_ms": fallback_elapsed_ms,
                "llm_called": True,
                "llm_skip_reason": None,
                "llm_status": "process_timeout",
                "fallback_used": True,
                "fallback_reason": "INTEGRATED_PROCESS_TIMEOUT",
            }
        )
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
    validation_failure = payload.get("validation_failure")
    llm_status = payload.get(
        "llm_status",
        "applied" if llm_called else "skipped",
    )
    fallback_used = payload.get("fallback_used", validation_failure is not None)
    fallback_reason = payload.get("fallback_reason")
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
        or (validation_failure is not None and not isinstance(validation_failure, dict))
        or not isinstance(llm_status, str)
        or llm_status not in _LLM_STATUSES
        or not isinstance(fallback_used, bool)
        or (fallback_reason is not None and not isinstance(fallback_reason, str))
        or (not fallback_used and fallback_reason is not None)
    ):
        raise BinaryRuntimeError("Integrated LLM binary returned an invalid transform payload.")
    response = {
        "normalized_text": normalized_text,
        "speech_text": speech_text,
        "model": selected_model,
        "elapsed_ms": float(elapsed_ms),
        "rule_elapsed_ms": float(rule_elapsed_ms),
        "llm_elapsed_ms": float(llm_elapsed_ms),
        "llm_called": llm_called,
        "llm_skip_reason": llm_skip_reason,
        "llm_status": llm_status,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
    }
    if validation_failure is not None:
        code = validation_failure.get("code")
        severity = validation_failure.get("severity")
        message = validation_failure.get("message")
        if not all(isinstance(value, str) and value for value in (code, severity, message)):
            raise BinaryRuntimeError("Integrated LLM binary returned an invalid validation failure payload.")
        response["validation_failure"] = {
            "code": code,
            "severity": severity,
            "message": message,
        }
    return response


def _rules_only_command(runtime_binary: Path, *, model: str | None) -> list[str]:
    command = [str(runtime_binary), "--json", "--rules-only"]
    if model is not None:
        command.extend(["--model", model])
    return command


def _positive_timeout_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise BinaryRuntimeError(f"{name} must be a number.") from exc
    if not math.isfinite(value) or value <= 0:
        raise BinaryRuntimeError(f"{name} must be greater than zero.")
    return value


def _log_validation_fallback(stderr: str) -> None:
    for match in _FALLBACK_LOG_RE.finditer(stderr):
        _LOGGER.warning(
            "level%s_validation_fallback code=%s severity=%s",
            match.group("level"),
            match.group("code"),
            match.group("severity"),
        )


def _parse_llm_stage_payload(raw_output: str) -> dict:
    if not raw_output:
        raise BinaryRuntimeError("Integrated LLM binary returned empty output")
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise BinaryRuntimeError(
            "Integrated LLM binary returned invalid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise BinaryRuntimeError("LLM stage binary returned a non-object payload.")
    return payload
