from __future__ import annotations

import importlib
import json
import os
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BINARY_NAME = "tts_preprocessor"
# API production runtime resolves and executes this packaged binary instead of
# importing engine.* source modules from the deployed server filesystem.
SOURCE_DEBUG_FALLBACK_ENV = "TTS_PREPROCESSOR_ALLOW_SOURCE_DEBUG_FALLBACK"
SOURCE_DEBUG_FALLBACK_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


class BinaryRuntimeError(RuntimeError):
    """Raised when the packaged runtime binary cannot be executed safely."""


def _iter_binary_candidates() -> list[Path]:
    candidates: list[Path] = []

    env_path = os.getenv("TTS_PREPROCESSOR_BINARY")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    candidates.append(ROOT_DIR / "dist" / DEFAULT_BINARY_NAME)
    candidates.append(ROOT_DIR / "packages" / "tts-preprocessor" / "bin" / DEFAULT_BINARY_NAME)

    return candidates


def resolve_binary_path() -> Path:
    for candidate in _iter_binary_candidates():
        resolved = candidate if candidate.is_absolute() else (ROOT_DIR / candidate).resolve()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved

    searched = ", ".join(str(path) for path in _iter_binary_candidates()) or "<none>"
    raise FileNotFoundError(f"No executable runtime binary found. Searched: {searched}")


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

    try:
        raw_output = _run_binary_command(command, text=text)
    except BinaryRuntimeError as exc:
        if not _should_fallback_to_source_debug(exc):
            raise
        if not _allow_source_debug_fallback():
            raise BinaryRuntimeError(
                "packaged runtime binary does not support debug output; "
                "source debug fallback is disabled by default for production runtime; "
                "rebuild or update the packaged binary. "
                f"Original binary error: {exc}"
            ) from exc
        return _run_source_debug_fallback(text)

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


def _should_fallback_to_source_debug(exc: BinaryRuntimeError) -> bool:
    return "unrecognized arguments: --include-debug" in str(exc)


def _allow_source_debug_fallback() -> bool:
    value = os.getenv(SOURCE_DEBUG_FALLBACK_ENV, "")
    return value.strip().lower() in SOURCE_DEBUG_FALLBACK_TRUE_VALUES


def _run_source_debug_fallback(text: str) -> dict:
    # Local/dev compatibility escape hatch only. Production default must use
    # the packaged binary and fail old binaries instead of importing sources.
    engine_main = importlib.import_module("engine.main")
    return engine_main.transform_debug(text)
