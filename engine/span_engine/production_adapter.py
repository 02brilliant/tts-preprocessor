from __future__ import annotations

from typing import Any

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace
from engine.span_engine.compare import build_span_debug, classify_compare_result

SUPPORTED_ROLLOUT_MODES = frozenset(
    {
        "legacy_default",
        "span_shadow_compare",
        "span_default",
    }
)


def transform_for_production(
    text: str,
    *,
    enable_prosody: bool = True,
    debug: bool = False,
) -> str | dict[str, Any]:
    _ = enable_prosody
    _ensure_text(text)

    if debug:
        try:
            output = transform_with_trace(text)
        except Exception as exc:
            return _fallback_transform_payload(text, exc)
        debug_dict = output_to_debug_dict(output)
        return {
            "ok": True,
            "input_text": text,
            "normalized_text": output.normalized_text,
            "debug": debug_dict,
        }

    return transform(text)


def transform_payload(payload: dict[str, Any], *, debug: bool = False) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")
    if "text" not in payload:
        raise KeyError("text")

    text = payload["text"]
    _ensure_text(text)

    result: dict[str, Any] = {
        "ok": True,
        "normalized_text": transform(text),
    }
    if debug:
        try:
            result["debug"] = output_to_debug_dict(transform_with_trace(text))
        except Exception as exc:
            result.update(_fallback_metadata(exc))
    return result


def normalize_rollout_mode(mode: str) -> str:
    if not isinstance(mode, str):
        raise TypeError("mode must be str")
    normalized = mode.strip().lower()
    if normalized not in SUPPORTED_ROLLOUT_MODES:
        raise ValueError(f"invalid rollout mode: {mode!r}")
    return normalized


def get_rollout_mode(default: str = "legacy_default") -> str:
    return normalize_rollout_mode(default)


def run_rollout_transform(
    text: str,
    *,
    mode: str = "legacy_default",
    legacy_transform: Any | None = None,
    include_debug: bool = False,
) -> dict[str, Any]:
    _ensure_text(text)
    normalized_mode = normalize_rollout_mode(mode)

    if normalized_mode == "legacy_default":
        return _run_legacy_default_rollout(
            text,
            legacy_transform=legacy_transform,
            include_debug=include_debug,
        )
    if normalized_mode == "span_shadow_compare":
        return _run_span_shadow_compare_rollout(
            text,
            legacy_transform=legacy_transform,
            include_debug=include_debug,
        )
    if normalized_mode == "span_default":
        return _run_span_default_rollout(
            text,
            legacy_transform=legacy_transform,
            include_debug=include_debug,
        )
    raise ValueError(f"invalid rollout mode: {mode!r}")


def run_rollout_payload(
    payload: dict[str, Any],
    *,
    mode: str = "legacy_default",
    legacy_transform: Any | None = None,
    include_debug: bool = False,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")
    if "text" not in payload:
        raise KeyError("text")

    text = payload["text"]
    _ensure_text(text)
    return run_rollout_transform(
        text,
        mode=mode,
        legacy_transform=legacy_transform,
        include_debug=include_debug,
    )


def run_shadow_compare(
    text: str,
    *,
    legacy_transform: Any | None = None,
    include_debug: bool = False,
) -> dict[str, Any]:
    _ensure_text(text)

    legacy_output: str | None = None
    legacy_error: str | None = None
    span_error: str | None = None
    span_debug: dict[str, Any] | None = None

    legacy_callable = legacy_transform if legacy_transform is not None else _identity_legacy
    try:
        legacy_output = legacy_callable(text)
    except Exception as exc:
        legacy_error = str(exc)

    try:
        span_output = transform_for_production(text)
    except Exception as exc:
        span_output = None
        span_error = str(exc)

    if include_debug and span_error is None:
        try:
            span_debug = build_span_debug(text)
        except Exception as exc:
            span_debug = _fallback_debug(text, exc)

    compare_result = classify_compare_result(
        input_text=text,
        legacy_output=legacy_output,
        span_output=span_output,
        span_debug=span_debug,
        legacy_error=legacy_error,
        span_error=span_error,
    )

    result = compare_result.to_dict()
    result["input_text"] = text
    result["production_output"] = legacy_output if legacy_error is None else None
    result["shadow"] = True
    if include_debug and span_debug is not None:
        result["span_debug"] = span_debug
    return result


def build_shadow_compare_payload(
    payload: dict[str, Any],
    *,
    legacy_transform: Any | None = None,
    include_debug: bool = False,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")
    if "text" not in payload:
        raise KeyError("text")

    text = payload["text"]
    _ensure_text(text)

    compare_result = run_shadow_compare(
        text,
        legacy_transform=legacy_transform,
        include_debug=include_debug,
    )
    result: dict[str, Any] = {
        "ok": True,
        "mode": "span_shadow_compare",
        "normalized_text": compare_result["production_output"],
        "span_output": compare_result["span_output"],
        "legacy_output": compare_result["legacy_output"],
        "compare": compare_result,
    }
    return result


def _ensure_text(text: Any) -> None:
    if not isinstance(text, str):
        raise TypeError("text must be a string")


def _run_legacy_default_rollout(
    text: str,
    *,
    legacy_transform: Any | None,
    include_debug: bool,
) -> dict[str, Any]:
    _ = include_debug
    legacy_callable = legacy_transform if legacy_transform is not None else _identity_legacy
    try:
        legacy_output = legacy_callable(text)
    except Exception as exc:
        return {
            "ok": False,
            "mode": "legacy_default",
            "input_text": text,
            "normalized_text": None,
            "production_output": None,
            "legacy_output": None,
            "span_output": None,
            "compare": None,
            "error": str(exc),
        }

    return {
        "ok": True,
        "mode": "legacy_default",
        "input_text": text,
        "normalized_text": legacy_output,
        "production_output": legacy_output,
        "legacy_output": legacy_output,
        "span_output": None,
        "compare": None,
        "error": None,
    }


def _run_span_shadow_compare_rollout(
    text: str,
    *,
    legacy_transform: Any | None,
    include_debug: bool,
) -> dict[str, Any]:
    compare_result = run_shadow_compare(
        text,
        legacy_transform=legacy_transform,
        include_debug=include_debug,
    )
    return {
        "ok": compare_result["production_output"] is not None,
        "mode": "span_shadow_compare",
        "input_text": text,
        "normalized_text": compare_result["production_output"],
        "production_output": compare_result["production_output"],
        "legacy_output": compare_result["legacy_output"],
        "span_output": compare_result["span_output"],
        "compare": compare_result,
        "error": compare_result["legacy_error"] if compare_result["production_output"] is None else None,
    }


def _run_span_default_rollout(
    text: str,
    *,
    legacy_transform: Any | None,
    include_debug: bool,
) -> dict[str, Any]:
    span_debug: dict[str, Any] | None = None
    try:
        span_output = transform_for_production(text)
    except Exception as exc:
        return {
            "ok": False,
            "mode": "span_default",
            "input_text": text,
            "normalized_text": None,
            "production_output": None,
            "legacy_output": None,
            "span_output": None,
            "compare": None,
            "error": str(exc),
        }

    if include_debug:
        try:
            span_debug = build_span_debug(text)
        except Exception as exc:
            span_debug = _fallback_debug(text, exc)

    legacy_output: str | None = None
    legacy_error: str | None = None
    compare: dict[str, Any] | None = None
    if legacy_transform is not None:
        try:
            legacy_output = legacy_transform(text)
        except Exception as exc:
            legacy_error = str(exc)

        compare_result = classify_compare_result(
            input_text=text,
            legacy_output=legacy_output,
            span_output=span_output,
            span_debug=span_debug,
            legacy_error=legacy_error,
            span_error=None,
        )
        compare = compare_result.to_dict()
        if include_debug and span_debug is not None:
            compare["span_debug"] = span_debug

    result = {
        "ok": True,
        "mode": "span_default",
        "input_text": text,
        "normalized_text": span_output,
        "production_output": span_output,
        "legacy_output": legacy_output,
        "span_output": span_output,
        "compare": compare,
        "error": None,
    }
    if include_debug and span_debug is not None:
        result["span_debug"] = span_debug
    return result


def _identity_legacy(text: str) -> str:
    return text


def _fallback_transform_payload(text: str, exc: Exception) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": True,
        "input_text": text,
        "normalized_text": text,
        "debug": _fallback_debug(text, exc),
    }
    payload.update(_fallback_metadata(exc))
    return payload


def _fallback_debug(text: str, exc: Exception) -> dict[str, Any]:
    return {
        "normalized_text": text,
        "fallback": "preserve_original",
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "error_stage": "transform",
    }


def _fallback_metadata(exc: Exception) -> dict[str, Any]:
    return {
        "fallback": "preserve_original",
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "error_stage": "transform",
    }


__all__ = [
    "SUPPORTED_ROLLOUT_MODES",
    "build_shadow_compare_payload",
    "get_rollout_mode",
    "normalize_rollout_mode",
    "run_rollout_payload",
    "run_rollout_transform",
    "run_shadow_compare",
    "transform_for_production",
    "transform_payload",
]
