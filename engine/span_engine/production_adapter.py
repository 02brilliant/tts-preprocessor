from __future__ import annotations

from typing import Any

from engine.span_engine.trace import output_to_debug_dict
from engine.span_engine.transform import (
    contains_hangul_syllable,
    recover_transform_output,
    transform,
    transform_with_trace,
)


def transform_for_production(
    text: str,
    *,
    enable_prosody: bool = True,
    debug: bool = False,
) -> str | dict[str, Any]:
    """Run the single production span engine in text or debug form."""
    _ = enable_prosody
    _ensure_text(text)

    if debug:
        try:
            output = transform_with_trace(text)
        except Exception as exc:
            return _recovered_transform_payload(text, exc)
        return {
            "ok": True,
            "input_text": text,
            "normalized_text": output.normalized_text,
            "debug": output_to_debug_dict(output),
        }

    try:
        return transform(text)
    except Exception as exc:
        return recover_transform_output(text, exc).normalized_text


def transform_payload(payload: dict[str, Any], *, debug: bool = False) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")
    if "text" not in payload:
        raise KeyError("text")

    text = payload["text"]
    _ensure_text(text)

    if debug:
        result = transform_for_production(text, debug=True)
        if not isinstance(result, dict):
            raise RuntimeError("production debug transform returned a non-object result")
        return result

    result = transform_for_production(text)
    if not isinstance(result, str):
        raise RuntimeError("production transform returned a non-text result")
    return {"ok": True, "normalized_text": result}


def _ensure_text(text: Any) -> None:
    if not isinstance(text, str):
        raise TypeError("text must be a string")


def _recovered_transform_payload(text: str, exc: Exception) -> dict[str, Any]:
    output = recover_transform_output(text, exc)
    fallback = (
        "segment_preserve"
        if contains_hangul_syllable(text)
        else "preserve_original"
    )
    debug_payload = output_to_debug_dict(output)
    debug_payload.update(_fallback_metadata(exc, fallback=fallback))
    payload: dict[str, Any] = {
        "ok": True,
        "input_text": text,
        "normalized_text": output.normalized_text,
        "debug": debug_payload,
    }
    payload.update(_fallback_metadata(exc, fallback=fallback))
    return payload


def _fallback_metadata(exc: Exception, *, fallback: str) -> dict[str, Any]:
    return {
        "fallback": fallback,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "error_stage": "transform",
    }


__all__ = ["transform_for_production", "transform_payload"]
