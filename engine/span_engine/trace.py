from __future__ import annotations

from typing import Any

from engine.span_engine.models import (
    ClaimCollisionLog,
    ClaimedRange,
    RenderPiece,
    ShadowUnit,
    SourceSpan,
    TraceLogEntry,
    TransformOutput,
    TransformTrace,
    ValidationLog,
)

TRACE_LOG_FIELDS = [
    "source_map_logs",
    "tokenization_logs",
    "shadow_logs",
    "claim_logs",
    "claim_collision_logs",
    "gate_logs",
    "parser_logs",
    "fallback_logs",
    "preserve_logs",
    "particle_exception_logs",
    "render_logs",
    "validation_logs",
    "prosody_logs",
    "bracket_filter_logs",
]


def span_to_dict(span: SourceSpan | None) -> dict[str, int] | None:
    if span is None:
        return None
    if not isinstance(span, SourceSpan):
        raise TypeError("span must be SourceSpan or None")
    return {"start": span.start, "end": span.end, "length": span.length}


def render_piece_to_dict(piece: RenderPiece) -> dict[str, Any]:
    if not isinstance(piece, RenderPiece):
        raise TypeError("piece must be RenderPiece")
    return {
        "text": piece.text,
        "provenance": piece.provenance,
        "source_span": span_to_dict(piece.source_span),
        "owner": piece.owner,
        "metadata": _json_safe(piece.metadata),
    }


def shadow_unit_to_dict(unit: ShadowUnit) -> dict[str, Any]:
    if not isinstance(unit, ShadowUnit):
        raise TypeError("unit must be ShadowUnit")
    return {"kind": unit.kind, "raw": unit.raw, "span": span_to_dict(unit.span)}


def validation_log_to_dict(log: ValidationLog) -> dict[str, Any]:
    if not isinstance(log, ValidationLog):
        raise TypeError("log must be ValidationLog")
    return {
        "kind": log.kind,
        "passed": log.passed,
        "expected": log.expected,
        "actual": log.actual,
        "span": span_to_dict(log.span),
        "reason": log.reason,
        "metadata": _json_safe(log.metadata),
    }


def claimed_range_to_dict(claim: ClaimedRange) -> dict[str, Any]:
    if not isinstance(claim, ClaimedRange):
        raise TypeError("claim must be ClaimedRange")
    return {
        "span": span_to_dict(claim.span),
        "owner": claim.owner,
        "claim_type": claim.claim_type,
        "surface_type": claim.surface_type,
        "reason": claim.reason,
        "reentry_allowed": claim.reentry_allowed,
    }


def claim_collision_log_to_dict(log: ClaimCollisionLog) -> dict[str, Any]:
    if not isinstance(log, ClaimCollisionLog):
        raise TypeError("log must be ClaimCollisionLog")
    return {
        "attempted_owner": log.attempted_owner,
        "attempted_span": span_to_dict(log.attempted_span),
        "existing_owner": log.existing_owner,
        "existing_span": span_to_dict(log.existing_span),
        "reason": log.reason,
        "metadata": _json_safe(log.metadata),
    }


def trace_log_entry_to_dict(entry: TraceLogEntry | dict[str, Any]) -> dict[str, Any]:
    if isinstance(entry, dict):
        return _json_safe(entry)
    if not isinstance(entry, TraceLogEntry):
        raise TypeError("entry must be TraceLogEntry or dict")
    return {
        "stage": entry.stage,
        "event": entry.event,
        "span": span_to_dict(entry.span),
        "raw": entry.raw,
        "owner": entry.owner,
        "surface_type": entry.surface_type,
        "decision": entry.decision,
        "reason": entry.reason,
        "action": entry.action,
        "provenance": entry.provenance,
        "expected": entry.expected,
        "actual": entry.actual,
        "metadata": _json_safe(entry.metadata),
    }


def trace_to_dict(trace: TransformTrace) -> dict[str, Any]:
    if not isinstance(trace, TransformTrace):
        raise TypeError("trace must be TransformTrace")
    return {
        field_name: _serialize_log_list(getattr(trace, field_name))
        for field_name in TRACE_LOG_FIELDS
    }


def output_to_debug_dict(output: TransformOutput) -> dict[str, Any]:
    if not isinstance(output, TransformOutput):
        raise TypeError("output must be TransformOutput")
    return {
        "normalized_text": output.normalized_text,
        "render_pieces": [render_piece_to_dict(piece) for piece in output.render_pieces],
        "trace": trace_to_dict(output.trace) if output.trace is not None else None,
    }


def build_span_debug(text: str) -> dict[str, Any]:
    """Build structured debug output using only the canonical span engine."""
    from engine.span_engine.transform import transform_with_trace

    return output_to_debug_dict(transform_with_trace(text))


def _serialize_log_list(logs: list[Any]) -> list[Any]:
    if not isinstance(logs, list):
        raise TypeError("trace log fields must be lists")
    return [_json_safe(log) for log in logs]


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, SourceSpan):
        return span_to_dict(value)
    if isinstance(value, RenderPiece):
        return render_piece_to_dict(value)
    if isinstance(value, ShadowUnit):
        return shadow_unit_to_dict(value)
    if isinstance(value, ValidationLog):
        return validation_log_to_dict(value)
    if isinstance(value, ClaimCollisionLog):
        return claim_collision_log_to_dict(value)
    if isinstance(value, ClaimedRange):
        return claimed_range_to_dict(value)
    if isinstance(value, TraceLogEntry):
        return trace_log_entry_to_dict(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    raise TypeError(f"unsupported debug serialization value: {type(value).__name__}")
