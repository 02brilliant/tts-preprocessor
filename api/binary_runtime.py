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
SUPPORTED_ROLLOUT_MODES = frozenset(
    {
        "legacy_default",
        "span_shadow_compare",
        "span_default",
    }
)


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
    """Run the packaged production binary with its default span_default contract."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    runtime_binary = binary_path or resolve_binary_path()
    return _run_binary_command([str(runtime_binary)], text=text)


def run_transform_binary_with_rollout(
    text: str,
    *,
    rollout_mode: str | None = None,
    include_debug: bool = False,
    binary_path: Path | None = None,
):
    """Run the packaged binary with an explicit rollout mode for smoke/debug probes."""
    if rollout_mode is None and not include_debug:
        return run_transform_binary(text, binary_path=binary_path)

    if rollout_mode is None:
        rollout_mode = "span_default"

    normalized_mode = _normalize_rollout_mode(rollout_mode)

    runtime_binary = binary_path or resolve_binary_path()
    command = [str(runtime_binary), "--rollout-mode", normalized_mode]
    if include_debug:
        command.append("--include-debug")

    try:
        raw_output = _run_binary_command(command, text=text)
    except BinaryRuntimeError as exc:
        if _should_fallback_to_source(exc):
            return _run_source_rollout_fallback(
                text,
                rollout_mode=normalized_mode,
                include_debug=include_debug,
            )
        raise

    if not include_debug:
        return raw_output

    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValueError("binary returned invalid rollout debug JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("binary returned non-object rollout debug payload")
    return payload


def _normalize_rollout_mode(mode: str) -> str:
    if not isinstance(mode, str):
        raise TypeError("rollout_mode must be str")
    normalized = mode.strip().lower()
    if normalized not in SUPPORTED_ROLLOUT_MODES:
        raise ValueError(f"invalid rollout mode: {mode!r}")
    return normalized


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


def _should_fallback_to_source(exc: BinaryRuntimeError) -> bool:
    message = str(exc)
    return "unrecognized arguments: --rollout-mode" in message or "unrecognized arguments: --include-debug" in message


def _run_source_rollout_fallback(
    text: str,
    *,
    rollout_mode: str,
    include_debug: bool,
):
    engine_main = importlib.import_module("engine.main")

    return engine_main.transform_with_rollout(
        text,
        mode=rollout_mode,
        include_debug=include_debug,
    )
