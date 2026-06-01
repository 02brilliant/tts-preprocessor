from __future__ import annotations

import re
from typing import Any

from engine.span_engine.brackets import (
    apply_final_bracket_filter,
    find_bracket_ranges,
    find_incomplete_bracket_ranges,
    protect_square_brackets_before_claim,
)
from engine.span_engine.claim_registry import SurfaceClaimRegistry
from engine.span_engine.claim_scanner import claim_surfaces
from engine.span_engine.date_time import build_time_gate_logs
from engine.span_engine.emergency import build_emergency_gate_logs
from engine.span_engine.event import build_event_gate_logs
from engine.span_engine.language_gate import (
    classify_lines,
    has_hyphenated_english_multi_colon_context,
    has_hangul_syllable,
    is_code_like_line,
    is_managed_dictionary_phrase,
    is_non_korean_prose_line,
    is_standalone_supported_token,
    transform_with_language_gate,
)
from engine.span_engine.models import TraceLogEntry, TransformOutput, ValidationLog
from engine.span_engine.parser import parse_candidates
from engine.span_engine.particle import apply_safe_post_surface_particle_exception
from engine.span_engine.public_number import build_public_number_gate_logs
from engine.prosody.paragraph import split_paragraphs
from engine.span_engine.prosody import apply_prosody_comma_adapter
from engine.span_engine.protected import protected_literal_spans
from engine.span_engine.render import join_render_pieces, render_tokens_with_surfaces
from engine.span_engine.shadow import build_shadow_buffer
from engine.span_engine.source_map import build_source_map, source_map_summary
from engine.span_engine.tokenizer import tokenize_immutable_spans, validate_token_coverage
from engine.span_engine.validation import validate_shadow

_SPACED_ASCII_SLASH_DELIMITER_RE = re.compile(r" +/ +")


def _ensure_str(text: Any) -> str:
    if not isinstance(text, str):
        raise TypeError("span_engine input must be str")
    return text


def transform(text: str) -> str:
    checked_text = _ensure_str(text)
    try:
        return transform_with_trace(checked_text).normalized_text
    except Exception:
        if has_hangul_syllable(checked_text):
            return _transform_hangul_with_segment_fallback(
                checked_text, RuntimeError("public_transform_exception")
            ).normalized_text
        return checked_text


def transform_with_trace(text: str) -> TransformOutput:
    checked_text = _ensure_str(text)
    try:
        output = _transform_with_language_gate_trace(checked_text)
    except Exception as exc:
        if has_hangul_syllable(checked_text):
            output = _transform_hangul_with_segment_fallback(checked_text, exc)
        else:
            raise
    return _apply_paragraph_split_to_output(output)


def _apply_paragraph_split_to_output(output: TransformOutput) -> TransformOutput:
    text = output.normalized_text
    if not has_hangul_syllable(text):
        return output
    return TransformOutput(
        normalized_text=split_paragraphs(text),
        render_pieces=output.render_pieces,
        trace=output.trace,
    )


def contains_hangul_syllable(text: str) -> bool:
    return has_hangul_syllable(text)


def may_whole_input_preserve(text: str, reason: str) -> bool:
    if contains_hangul_syllable(text):
        return False
    return reason in {
        "global_no_hangul_bypass",
        "whole_input_absolute_preserve",
        "non_korean_prose_global_bypass",
        "code_like_global_bypass",
    }


def _transform_with_language_gate_trace(
    text: str, *, split_spaced_slash_boundaries: bool = True
) -> TransformOutput:
    stripped = text.strip()
    if (
        len(stripped) >= 3
        and (
            (stripped.startswith("[") and stripped.endswith("]"))
            or (stripped.startswith("(") and stripped.endswith(")"))
        )
        and (
            is_standalone_supported_token(stripped[1:-1].strip())
            or re.fullmatch(r"[+\-−－]?\d+(?:\.\d+)?", stripped[1:-1].strip())
        )
    ):
        return _transform_core_with_trace(text)
    if stripped and not is_code_like_line(stripped) and is_standalone_supported_token(stripped):
        return _transform_core_with_trace(text)
    if not has_hangul_syllable(text) and is_code_like_line(text):
        core_output = _try_core_trace_for_whole_input(text, text)
        if core_output is not None:
            return core_output
        return TransformOutput(
            normalized_text=text,
            render_pieces=[_preserve_render_piece(text, 0, len(text))],
            trace=None,
        )
    if not has_hangul_syllable(text) and is_managed_dictionary_phrase(text):
        return _transform_core_with_trace(text)
    if not has_hangul_syllable(text) and is_non_korean_prose_line(text):
        if has_hyphenated_english_multi_colon_context(text):
            return _transform_core_with_trace(text)
        return TransformOutput(
            normalized_text=text,
            render_pieces=[_preserve_render_piece(text, 0, len(text))],
            trace=None,
        )
    if not has_hangul_syllable(text):
        return _transform_core_with_trace(text)
    lines = classify_lines(text)
    non_empty = [line for line in lines if line.text.strip()]
    if non_empty and all(
        line.has_hangul and not line.is_numeric_list and not line.is_code_like
        for line in non_empty
    ):
        return _transform_core_or_spaced_slash_boundaries_with_trace(
            text, split_spaced_slash_boundaries=split_spaced_slash_boundaries
        )

    def core_transform(segment: str) -> str:
        return _transform_core_or_spaced_slash_boundaries_with_trace(
            segment, split_spaced_slash_boundaries=split_spaced_slash_boundaries
        ).normalized_text

    normalized_text = transform_with_language_gate(text, core_transform)
    core_output = _try_core_trace_for_whole_input(text, normalized_text)
    if core_output is not None:
        return core_output
    return TransformOutput(
        normalized_text=normalized_text,
        render_pieces=[
            _preserve_render_piece(normalized_text, 0, len(text)),
        ],
        trace=None,
    )


def _transform_core_or_spaced_slash_boundaries_with_trace(
    text: str, *, split_spaced_slash_boundaries: bool
) -> TransformOutput:
    if split_spaced_slash_boundaries:
        split_output = _transform_spaced_slash_boundaries_with_trace(text)
        if split_output is not None:
            return split_output
    return _transform_core_with_trace(text)


def _transform_spaced_slash_boundaries_with_trace(text: str) -> TransformOutput | None:
    if not has_hangul_syllable(text):
        return None

    parts = _split_on_unprotected_spaced_ascii_slash(text)
    if parts is None:
        return None

    transformed: list[str] = []
    for raw, is_delimiter in parts:
        if is_delimiter or not raw or not raw.strip():
            transformed.append(raw)
            continue
        transformed.append(
            _transform_with_language_gate_trace(
                raw, split_spaced_slash_boundaries=False
            ).normalized_text
        )
    normalized_text = "".join(transformed)
    return TransformOutput(
        normalized_text=normalized_text,
        render_pieces=[_preserve_render_piece(normalized_text, 0, len(text))],
        trace=None,
    )


def _split_on_unprotected_spaced_ascii_slash(
    text: str,
) -> list[tuple[str, bool]] | None:
    protected_ranges = _spaced_slash_protected_ranges(text)
    parts: list[tuple[str, bool]] = []
    cursor = 0
    matched = False

    for match in _SPACED_ASCII_SLASH_DELIMITER_RE.finditer(text):
        if _span_overlaps_ranges(match.start(), match.end(), protected_ranges):
            continue
        parts.append((text[cursor : match.start()], False))
        parts.append((match.group(0), True))
        cursor = match.end()
        matched = True

    if not matched:
        return None

    parts.append((text[cursor:], False))
    return parts


def _spaced_slash_protected_ranges(text: str) -> list[tuple[int, int]]:
    ranges = [(span.start, span.end) for span in protected_literal_spans(text)]
    ranges.extend(
        (bracket_range.span.start, bracket_range.span.end)
        for bracket_range in find_bracket_ranges(text)
    )
    ranges.extend(
        (bracket_range.span.start, bracket_range.span.end)
        for bracket_range in find_incomplete_bracket_ranges(text)
    )
    return ranges


def _span_overlaps_ranges(
    start: int, end: int, ranges: list[tuple[int, int]]
) -> bool:
    return any(
        start < range_end and range_start < end
        for range_start, range_end in ranges
    )


def _try_core_trace_for_whole_input(
    text: str, normalized_text: str
) -> TransformOutput | None:
    try:
        output = _transform_core_with_trace(text)
    except Exception:
        return None
    if output.normalized_text == normalized_text:
        return output
    return None


def _transform_hangul_with_segment_fallback(text: str, exc: Exception) -> TransformOutput:
    from engine.span_engine.models import TransformTrace

    transformed: list[str] = []
    segment_failures: list[dict[str, Any]] = []
    for start, end in _fallback_segments(text):
        segment = text[start:end]
        if not segment:
            continue
        if not has_hangul_syllable(segment):
            transformed.append(segment)
            continue
        try:
            transformed.append(_transform_core_with_trace(segment).normalized_text)
        except Exception as segment_exc:
            segment_failures.append(
                {
                    "start": start,
                    "end": end,
                    "error_type": type(segment_exc).__name__,
                    "error_message": str(segment_exc),
                }
            )
            transformed.append(segment)
    normalized_text = "".join(transformed)
    trace = TransformTrace()
    trace.fallback_logs.append(
        TraceLogEntry(
            stage="fallback",
            event="blocked_whole_input_fallback_for_hangul_input",
            span=_span(0, len(text)),
            raw=text,
            decision="blocked",
            reason="hangul_input_whole_fallback_prohibited",
            action="segment_fallback",
            metadata={
                "status": "segment_fallback",
                "fallback_stage": "transform_with_trace",
                "fallback_reason": type(exc).__name__,
                "fallback_span": (0, len(text)),
                "fallback_raw": text,
                "whole_input_fallback_attempted": True,
                "whole_input_fallback_allowed": False,
                "blocked_whole_input_fallback_for_hangul_input": True,
                "segment_failures": segment_failures,
            },
        )
    )
    return TransformOutput(
        normalized_text=normalized_text,
        render_pieces=[_preserve_render_piece(normalized_text, 0, len(text))],
        trace=trace,
    )


def _fallback_segments(text: str) -> list[tuple[int, int]]:
    boundaries: list[tuple[int, int]] = []
    start = 0
    for match in re.finditer(r"(?<=[.!?。！？])\s+|\n+", text):
        end = match.end()
        boundaries.append((start, end))
        start = end
    if start < len(text):
        boundaries.append((start, len(text)))
    if not boundaries:
        return [(0, 0)]
    return boundaries


def _span(start: int, end: int):
    from engine.span_engine.models import SourceSpan

    return SourceSpan(start, end)


def _preserve_render_piece(text: str, start: int, end: int):
    from engine.span_engine.models import RenderPiece, SourceSpan

    return RenderPiece(
        text=text,
        provenance="ORIGINAL_BOUNDARY",
        source_span=SourceSpan(start, end),
    )


def _transform_core_with_trace(text: str) -> TransformOutput:
    checked_text = _ensure_str(text)
    source_chars = build_source_map(checked_text)
    tokens = tokenize_immutable_spans(checked_text, source_chars)
    validate_token_coverage(checked_text, tokens)
    bracket_ranges = find_bracket_ranges(checked_text)
    incomplete_bracket_ranges = find_incomplete_bracket_ranges(checked_text)
    registry = SurfaceClaimRegistry()
    shadow = build_shadow_buffer(tokens)
    protect_square_brackets_before_claim(registry, bracket_ranges)
    candidates = claim_surfaces(
        checked_text,
        tokens,
        registry,
        excluded_ranges=bracket_ranges + incomplete_bracket_ranges,
    )
    surfaces = parse_candidates(checked_text, candidates)
    pieces = render_tokens_with_surfaces(checked_text, tokens, surfaces)
    particle_result = apply_safe_post_surface_particle_exception(pieces)
    pieces = particle_result.pieces
    consumed_shadow_spans = _surface_internal_shadow_spans(surfaces, shadow)
    validation = validate_shadow(
        pieces,
        shadow,
        consumed_particle_spans=particle_result.consumed_spans,
        consumed_shadow_spans=consumed_shadow_spans,
    )
    if not validation.passed:
        raise RuntimeError("shadow validation failed")
    prosody_result = apply_prosody_comma_adapter(pieces, checked_text, bracket_ranges)
    pieces = prosody_result.pieces
    pre_filter_text = join_render_pieces(pieces)
    bracket_filter = apply_final_bracket_filter(pieces, bracket_ranges)
    normalized_text = bracket_filter.normalized_text

    from engine.span_engine.models import TransformTrace

    trace = TransformTrace()
    trace.claim_logs.extend(registry.claims)
    trace.claim_collision_logs.extend(registry.collision_logs)
    trace.gate_logs.extend(
        build_time_gate_logs(checked_text, bracket_ranges + incomplete_bracket_ranges)
    )
    trace.gate_logs.extend(
        build_event_gate_logs(checked_text, bracket_ranges + incomplete_bracket_ranges)
    )
    trace.gate_logs.extend(
        build_emergency_gate_logs(checked_text, bracket_ranges + incomplete_bracket_ranges)
    )
    trace.gate_logs.extend(
        build_public_number_gate_logs(
            checked_text, bracket_ranges + incomplete_bracket_ranges
        )
    )
    trace.particle_exception_logs.extend(particle_result.logs)
    trace.prosody_logs.extend(prosody_result.logs)
    trace.bracket_filter_logs.extend(bracket_filter.logs)
    trace.parser_logs.extend(
        TraceLogEntry(
            stage="parser",
            event="surface_parsed",
            span=surface.span,
            raw=surface.raw,
            owner=surface.owner,
            surface_type=surface.surface_type,
            decision="success",
            reason="phase7_owner_parse",
            action="create_surface",
            metadata={"reading": surface.reading},
        )
        for surface in surfaces
    )
    trace.source_map_logs.append(
        TraceLogEntry(
            stage="source_map",
            event="source_map_built",
            decision="pass",
            reason="phase6_source_map_summary",
            metadata=source_map_summary(checked_text, source_chars),
        )
    )
    trace.tokenization_logs.append(
        TraceLogEntry(
            stage="tokenization",
            event="tokenization_complete",
            decision="pass",
            reason="phase6_tokenization_summary",
            metadata={
                "token_count": len(tokens),
                "kind_counts": _count_by_attr(tokens, "kind"),
            },
        )
    )
    trace.tokenization_logs.extend(
        TraceLogEntry(
            stage="tokenization",
            event="token_created",
            span=token.span,
            raw=token.raw,
            surface_type=token.surface_type,
            decision="preserve",
            reason="phase3_pass_through_tokenization",
            metadata={"token_type": token.kind, "immutable": token.immutable},
        )
        for token in tokens
    )
    trace.shadow_logs.append(
        TraceLogEntry(
            stage="shadow",
            event="shadow_buffer_built",
            decision="pass",
            reason="phase6_shadow_summary",
            metadata={"shadow_unit_count": len(shadow)},
        )
    )
    trace.shadow_logs.extend(
        TraceLogEntry(
            stage="shadow",
            event="shadow_unit_created",
            span=unit.span,
            raw=unit.raw,
            decision="preserve",
            reason="phase4_shadow_preservation_target",
            metadata={"shadow_type": unit.kind},
        )
        for unit in shadow
    )
    trace.render_logs.append(
        TraceLogEntry(
            stage="render",
            event="surface_render_complete",
            decision="pass",
            reason="phase7_surface_render_summary",
            metadata={
                "render_piece_count": len(pieces),
                "pre_filter_text": pre_filter_text,
                "generated_piece_count": sum(
                    1
                    for piece in pieces
                    if piece.provenance
                    in {"GENERATED_READING", "GENERATED_PARTICLE", "GENERATED_PUNCT"}
                ),
            },
        )
    )
    trace.render_logs.extend(
        TraceLogEntry(
            stage="render",
            event="render_piece_created",
            span=piece.source_span,
            raw=piece.text,
            owner=piece.owner,
            provenance=piece.provenance,
            decision=(
                "render_generated"
                if piece.provenance.startswith("GENERATED_")
                else "render_original"
            ),
            reason="phase7_surface_render",
        )
        for piece in pieces
    )
    trace.validation_logs.append(
        ValidationLog(
            kind="SHADOW_VALIDATION",
            passed=validation.passed,
            reason="phase6_validation_summary",
            metadata={"passed": validation.passed, "log_count": len(validation.logs)},
        )
    )
    trace.validation_logs.extend(validation.logs)
    return TransformOutput(normalized_text=normalized_text, render_pieces=pieces, trace=trace)


def _count_by_attr(values: list[Any], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(getattr(value, attr))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _surface_internal_shadow_spans(surfaces: list[Any], shadow: list[Any]) -> set[tuple[int, int]]:
    consumed: set[tuple[int, int]] = set()
    for surface in surfaces:
        for unit in shadow:
            if (
                getattr(surface, "owner", None) == "currency"
                and getattr(surface, "metadata", {}).get("reason")
                in {
                    "decimal_large_unit_krw_expansion",
                    "large_unit_currency_suffix",
                }
                and _spans_overlap(surface.span.start, surface.span.end, unit.span.start, unit.span.end)
            ):
                consumed.add((unit.span.start, unit.span.end))
                continue
            if (
                getattr(surface, "owner", None) == "currency"
                and getattr(surface, "metadata", {}).get("reason")
                in {
                    "decimal_large_unit_krw_expansion",
                    "large_unit_currency_suffix",
                }
                and surface.span.start <= unit.span.start
                and unit.span.end <= surface.span.end
            ):
                consumed.add((unit.span.start, unit.span.end))
                continue
            if (
                getattr(surface, "owner", None) == "large_unit_atomic"
                and _spans_overlap(surface.span.start, surface.span.end, unit.span.start, unit.span.end)
            ):
                consumed.add((unit.span.start, unit.span.end))
                continue
            if (
                getattr(surface, "owner", None) == "counter_noun"
                and _spans_overlap(surface.span.start, surface.span.end, unit.span.start, unit.span.end)
            ):
                consumed.add((unit.span.start, unit.span.end))
                continue
            if (
                getattr(unit, "kind", None) == "KOREAN_SPACE"
                and surface.span.start <= unit.span.start
                and unit.span.end <= surface.span.end
            ):
                consumed.add((unit.span.start, unit.span.end))
                continue
            if (
                getattr(surface, "owner", None) == "numeric_suffix"
                and getattr(surface, "metadata", {}).get("reason")
                == "prefixed_ordinal_numeric_suffix"
                and _spans_overlap(surface.span.start, surface.span.end, unit.span.start, unit.span.end)
            ):
                consumed.add((unit.span.start, unit.span.end))
    return consumed


def _spans_overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return left_start < right_end and right_start < left_end
