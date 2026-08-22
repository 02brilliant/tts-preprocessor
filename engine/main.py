from __future__ import annotations

from typing import Any


def transform(text: str) -> str:
    """Normalize text through the canonical production span engine."""
    from engine.span_engine.production_adapter import transform_for_production

    result = transform_for_production(text)
    if not isinstance(result, str):
        raise RuntimeError("production transform returned a non-text result")
    return result


def transform_debug(text: str) -> dict[str, Any]:
    """Normalize text and return the canonical span debug payload."""
    from engine.span_engine.production_adapter import transform_for_production

    result = transform_for_production(text, debug=True)
    if not isinstance(result, dict):
        raise RuntimeError("production debug transform returned a non-object result")
    return result


def transform_simplified(text: str) -> str:
    """Normalize text without general English pronunciation fallbacks."""
    from engine.span_engine.production_adapter import transform_for_production
    from engine.span_engine.profile import engine_profile

    with engine_profile("simplified"):
        result = transform_for_production(text)
    if not isinstance(result, str):
        raise RuntimeError("simplified production transform returned a non-text result")
    return result


def transform_simplified_debug(text: str) -> dict[str, Any]:
    """Return the simplified engine's canonical span debug payload."""
    from engine.span_engine.production_adapter import transform_for_production
    from engine.span_engine.profile import engine_profile

    with engine_profile("simplified"):
        result = transform_for_production(text, debug=True)
    if not isinstance(result, dict):
        raise RuntimeError("simplified production debug transform returned a non-object result")
    return result


__all__ = [
    "transform",
    "transform_debug",
    "transform_simplified",
    "transform_simplified_debug",
]
