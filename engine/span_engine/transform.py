from __future__ import annotations

import re
from typing import Any

from engine.span_engine.arithmetic import (
    is_invalid_basic_arithmetic_expression_text,
    is_strict_basic_arithmetic_expression,
    unsupported_parenthesized_arithmetic_spans,
)
from engine.span_engine.brackets import (
    apply_final_bracket_filter,
    find_bracket_ranges,
    find_incomplete_bracket_ranges,
    is_code_like_curly_bracket,
    protect_non_parenthesis_brackets_before_claim,
)
from engine.span_engine.claim_registry import SurfaceClaimRegistry
from engine.span_engine.claim_scanner import claim_surfaces
from engine.span_engine.date_time import build_time_gate_logs
from engine.span_engine.contextual_number_unit import build_contextual_decision_logs
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
from engine.span_engine.models import (
    RenderPiece,
    SourceSpan,
    Surface,
    TraceLogEntry,
    TransformOutput,
    ValidationLog,
)
from engine.span_engine.parser import parse_candidates
from engine.span_engine.particle import apply_safe_post_surface_particle_exception
from engine.span_engine.public_number import build_public_number_gate_logs
from engine.prosody.paragraph import (
    normalize_user_newline_semantics,
    split_paragraphs,
)
from engine.span_engine.prosody import apply_prosody_comma_adapter
from engine.span_engine.prosody_extra import apply_extra_prosody_comma_adapter
from engine.span_engine.protected import protected_literal_spans
from engine.span_engine.render import join_render_pieces, render_tokens_with_surfaces
from engine.span_engine.sentence_final_slash import sentence_final_slash_spans
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
    except Exception as exc:
        return recover_transform_output(checked_text, exc).normalized_text


def transform_with_trace(text: str) -> TransformOutput:
    checked_text = _ensure_str(text)
    normalized_input = normalize_user_newline_semantics(checked_text)
    try:
        output = _transform_with_language_gate_trace(normalized_input)
    except Exception as exc:
        output = recover_transform_output(normalized_input, exc)
    return _apply_paragraph_split_to_output(output)


def recover_transform_output(text: str, exc: Exception) -> TransformOutput:
    checked_text = _ensure_str(text)
    if has_hangul_syllable(checked_text):
        return _transform_hangul_with_segment_fallback(checked_text, exc)
    return _whole_input_preserve_output(
        checked_text,
        exc,
        reason="global_no_hangul_bypass",
    )


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
    if reason == "whole_input_absolute_preserve":
        return True
    if contains_hangul_syllable(text):
        return False
    return reason in {
        "global_no_hangul_bypass",
        "non_korean_prose_global_bypass",
        "code_like_global_bypass",
    }


def _transform_with_language_gate_trace(
    text: str, *, split_spaced_slash_boundaries: bool = True
) -> TransformOutput:
    stripped = text.strip()
    if any(
        text[span.start : span.end].startswith("```")
        for span in protected_literal_spans(text)
    ):
        return _transform_core_with_trace(text)
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
    if stripped and is_strict_basic_arithmetic_expression(stripped):
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
    if (
        not has_hangul_syllable(text)
        and stripped
        and any(char in stripped for char in "()")
        and not (stripped.startswith("(") and stripped.endswith(")"))
        and (
            any(char in stripped for char in "+-×X*÷=^/")
            or bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\([^()]*\)", stripped))
        )
        and is_invalid_basic_arithmetic_expression_text(stripped)
    ):
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


def _whole_input_preserve_output(
    text: str,
    exc: Exception,
    *,
    reason: str,
) -> TransformOutput:
    from engine.span_engine.models import TransformTrace

    if not may_whole_input_preserve(text, reason):
        raise exc
    trace = TransformTrace()
    trace.fallback_logs.append(
        TraceLogEntry(
            stage="fallback",
            event="whole_input_preserve_allowed",
            span=_span(0, len(text)),
            raw=text,
            decision="preserve",
            reason=reason,
            action="preserve_original",
            metadata={
                "status": "whole_input_preserve",
                "fallback_reason": type(exc).__name__,
                "error_message": str(exc),
            },
        )
    )
    return TransformOutput(
        normalized_text=text,
        render_pieces=[_preserve_render_piece(text, 0, len(text))],
        trace=trace,
    )


def _preserved_failed_segment(
    text: str, start: int, end: int, exc: Exception
) -> tuple[str, list[RenderPiece], dict[str, Any]]:
    segment_text = text[start:end]
    return (
        segment_text,
        [_preserve_render_piece(segment_text, start, end)],
        {
            "start": start,
            "end": end,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        },
    )


def _segment_fallback_trace_log(
    text: str,
    exc: Exception,
    segment_failures: list[dict[str, Any]],
    segment_recoveries: list[dict[str, Any]],
) -> TraceLogEntry:
    return TraceLogEntry(
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
            "fallback_error_message": str(exc),
            "fallback_span": (0, len(text)),
            "fallback_raw": text,
            "whole_input_fallback_attempted": True,
            "whole_input_fallback_allowed": False,
            "blocked_whole_input_fallback_for_hangul_input": True,
            "segment_failures": segment_failures,
            "segment_recoveries": segment_recoveries,
        },
    )


def _transform_hangul_with_segment_fallback(text: str, exc: Exception) -> TransformOutput:
    from engine.span_engine.models import TransformTrace

    transformed: list[str] = []
    render_pieces: list[RenderPiece] = []
    segment_failures: list[dict[str, Any]] = []
    segment_recoveries: list[dict[str, Any]] = []

    for start, end in _fallback_segments(text):
        try:
            segment_text, segment_pieces = _transform_fallback_segment(
                text, start, end
            )
        except Exception:
            for sub_start, sub_end in _fallback_subsegments(text, start, end):
                try:
                    segment_text, segment_pieces = _transform_fallback_segment(
                        text, sub_start, sub_end
                    )
                    status = (
                        "preserved_boundary"
                        if text[sub_start:sub_end].isspace()
                        else "recovered"
                    )
                    segment_recoveries.append(
                        {"start": sub_start, "end": sub_end, "status": status}
                    )
                except Exception as segment_exc:
                    segment_text, segment_pieces, failure = (
                        _preserved_failed_segment(
                            text, sub_start, sub_end, segment_exc
                        )
                    )
                    segment_failures.append(failure)
                transformed.append(segment_text)
                render_pieces.extend(segment_pieces)
            continue

        transformed.append(segment_text)
        render_pieces.extend(segment_pieces)
        segment_recoveries.append(
            {"start": start, "end": end, "status": "recovered"}
        )

    normalized_text = "".join(transformed)
    trace = TransformTrace()
    trace.fallback_logs.append(
        _segment_fallback_trace_log(
            text, exc, segment_failures, segment_recoveries
        )
    )
    return TransformOutput(
        normalized_text=normalized_text,
        render_pieces=render_pieces,
        trace=trace,
    )


def _transform_fallback_segment(
    text: str, start: int, end: int
) -> tuple[str, list[RenderPiece]]:
    segment = text[start:end]
    if not segment:
        return "", []
    if segment.isspace():
        return segment, [_preserve_render_piece(segment, start, end)]
    output = _transform_core_with_trace(segment)
    return (
        output.normalized_text,
        [_offset_render_piece(piece, start) for piece in output.render_pieces],
    )


def _offset_render_piece(piece: RenderPiece, offset: int) -> RenderPiece:
    source_span = piece.source_span
    if source_span is not None:
        source_span = SourceSpan(
            source_span.start + offset,
            source_span.end + offset,
        )
    return RenderPiece(
        text=piece.text,
        provenance=piece.provenance,
        source_span=source_span,
        owner=piece.owner,
        metadata=dict(piece.metadata),
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
    return boundaries or [(0, len(text))]


def _fallback_subsegments(
    text: str, start: int, end: int
) -> list[tuple[int, int]]:
    return [
        (start + match.start(), start + match.end())
        for match in re.finditer(r"\s+|\S+", text[start:end])
    ]


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


def _render_piece_trace_log(piece: RenderPiece) -> TraceLogEntry:
    return TraceLogEntry(
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


def _parser_trace_log(surface: Surface) -> TraceLogEntry:
    return TraceLogEntry(
        stage="parser",
        event="surface_parsed",
        span=surface.span,
        raw=surface.raw,
        owner=surface.owner,
        surface_type=surface.surface_type,
        decision="success",
        reason="phase7_owner_parse",
        action="create_surface",
        metadata={
            "reading": surface.reading,
            **{
                key: surface.metadata[key]
                for key in (
                    "sign_profile",
                    "numeric_form",
                    "sign_surface",
                    "operand_kinds",
                    "operator_kinds",
                    "has_equality",
                )
                if key in surface.metadata
            },
        },
    )


def _transform_core_with_trace(text: str) -> TransformOutput:
    checked_text = _ensure_str(text)
    source_chars = build_source_map(checked_text)
    tokens = tokenize_immutable_spans(checked_text, source_chars)
    validate_token_coverage(checked_text, tokens)
    bracket_ranges = find_bracket_ranges(checked_text)
    incomplete_bracket_ranges = find_incomplete_bracket_ranges(checked_text)
    unsupported_parenthesized_spans = unsupported_parenthesized_arithmetic_spans(
        checked_text
    )
    active_bracket_ranges = [
        bracket_range
        for bracket_range in bracket_ranges
        if not any(
            bracket_range.span.start < span.end
            and span.start < bracket_range.span.end
            for span in unsupported_parenthesized_spans
        )
    ]
    presentation_bracket_ranges = [
        bracket_range
        for bracket_range in active_bracket_ranges
        if not is_code_like_curly_bracket(bracket_range)
    ]
    registry = SurfaceClaimRegistry()
    shadow = build_shadow_buffer(tokens)
    protect_non_parenthesis_brackets_before_claim(
        registry, presentation_bracket_ranges
    )
    candidates = claim_surfaces(
        checked_text,
        tokens,
        registry,
        excluded_ranges=presentation_bracket_ranges + incomplete_bracket_ranges,
    )
    surfaces = parse_candidates(checked_text, candidates)
    pieces = render_tokens_with_surfaces(checked_text, tokens, surfaces)
    slash_alias_logs: list[TraceLogEntry] = []
    pieces, slash_alias_logs = _apply_sentence_final_slash_punctuation_alias(
        pieces, checked_text, active_bracket_ranges + incomplete_bracket_ranges
    )
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
    prosody_result = apply_prosody_comma_adapter(pieces, checked_text, active_bracket_ranges)
    pieces = prosody_result.pieces
    extra_prosody_result = apply_extra_prosody_comma_adapter(
        pieces, checked_text, active_bracket_ranges
    )
    pieces = extra_prosody_result.pieces
    pre_filter_text = join_render_pieces(pieces)
    bracket_filter = apply_final_bracket_filter(pieces, presentation_bracket_ranges)
    normalized_text = bracket_filter.normalized_text

    from engine.span_engine.models import TransformTrace

    trace = TransformTrace()
    trace.claim_logs.extend(registry.claims)
    trace.claim_collision_logs.extend(registry.collision_logs)
    trace.gate_logs.extend(
        build_time_gate_logs(checked_text, active_bracket_ranges + incomplete_bracket_ranges)
    )
    trace.gate_logs.extend(
        build_event_gate_logs(checked_text, active_bracket_ranges + incomplete_bracket_ranges)
    )
    trace.gate_logs.extend(
        build_emergency_gate_logs(checked_text, active_bracket_ranges + incomplete_bracket_ranges)
    )
    trace.gate_logs.extend(
        build_public_number_gate_logs(
            checked_text, active_bracket_ranges + incomplete_bracket_ranges
        )
    )
    trace.particle_exception_logs.extend(particle_result.logs)
    trace.prosody_logs.extend(prosody_result.logs)
    trace.prosody_logs.extend(extra_prosody_result.logs)
    trace.bracket_filter_logs.extend(bracket_filter.logs)
    trace.parser_logs.extend(_parser_trace_log(surface) for surface in surfaces)
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
    trace.contextual_decision_logs.extend(
        build_contextual_decision_logs(candidates, normalized_text)
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
    trace.render_logs.extend(slash_alias_logs)
    trace.render_logs.extend(_render_piece_trace_log(piece) for piece in pieces)
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


def _apply_sentence_final_slash_punctuation_alias(
    pieces: list[RenderPiece],
    raw_text: str,
    bracket_ranges: list[Any],
) -> tuple[list[RenderPiece], list[TraceLogEntry]]:
    protected_ranges = _sentence_final_slash_protected_ranges(raw_text, bracket_ranges)
    slash_spans = sentence_final_slash_spans(raw_text, protected_ranges)
    if not slash_spans:
        return pieces, []

    aliased_pieces: list[RenderPiece] = []
    logs: list[TraceLogEntry] = []
    slash_index = 0
    for piece in pieces:
        if piece.source_span is None or slash_index >= len(slash_spans):
            aliased_pieces.append(piece)
            continue

        source_start = piece.source_span.start
        source_end = piece.source_span.end
        if source_end <= slash_spans[slash_index].start:
            aliased_pieces.append(piece)
            continue

        current_start = source_start
        replaced = False
        while (
            slash_index < len(slash_spans)
            and slash_spans[slash_index].start < source_end
        ):
            slash_span = slash_spans[slash_index]
            if slash_span.end <= source_start:
                slash_index += 1
                continue
            if slash_span.start < source_start or source_end < slash_span.end:
                break

            if current_start < slash_span.start:
                aliased_pieces.append(
                    _copy_original_piece_fragment(
                        piece, raw_text, current_start, slash_span.start
                    )
                )
            aliased_pieces.append(
                RenderPiece(
                    text=".",
                    provenance="GENERATED_PUNCT",
                    source_span=slash_span,
                    owner="sentence_final_slash",
                    metadata={"reason": "sentence_final_slash"},
                )
            )
            logs.append(
                TraceLogEntry(
                    stage="render",
                    event="sentence_final_slash_alias_applied",
                    span=slash_span,
                    raw=raw_text[slash_span.start : slash_span.end],
                    owner="sentence_final_slash",
                    provenance="GENERATED_PUNCT",
                    decision="render_generated",
                    reason="sentence_final_slash",
                    action="emit_generated_period",
                )
            )
            current_start = slash_span.end
            slash_index += 1
            replaced = True

        if not replaced:
            aliased_pieces.append(piece)
            continue
        if current_start < source_end:
            aliased_pieces.append(
                _copy_original_piece_fragment(
                    piece, raw_text, current_start, source_end
                )
            )

    if slash_index < len(slash_spans):
        return pieces, []
    return aliased_pieces, logs


def _copy_original_piece_fragment(
    piece: RenderPiece, raw_text: str, start: int, end: int
) -> RenderPiece:
    return RenderPiece(
        text=raw_text[start:end],
        provenance=piece.provenance,
        source_span=SourceSpan(start, end),
        owner=piece.owner,
        metadata=dict(piece.metadata),
    )


def _sentence_final_slash_protected_ranges(
    text: str, bracket_ranges: list[Any]
) -> list[tuple[int, int]]:
    ranges = [(span.start, span.end) for span in protected_literal_spans(text)]
    ranges.extend(
        (bracket_range.span.start, bracket_range.span.end)
        for bracket_range in bracket_ranges
    )
    return ranges


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
                getattr(surface, "owner", None)
                in {
                    "large_unit_atomic",
                    "mixed_integer_atomic",
                    "mixed_decimal_atomic",
                    "phrase_dictionary",
                }
                and _spans_overlap(surface.span.start, surface.span.end, unit.span.start, unit.span.end)
            ):
                consumed.add((unit.span.start, unit.span.end))
                continue
            if (
                getattr(surface, "owner", None) == "parenthesized_hangul_alias"
                and getattr(surface, "metadata", {}).get("consume_parenthetical_alias")
                is True
                and _spans_overlap(
                    surface.span.start, surface.span.end, unit.span.start, unit.span.end
                )
            ):
                consumed.add((unit.span.start, unit.span.end))
                continue
            if (
                getattr(surface, "owner", None) in {"counter_noun", "multiplier"}
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
                in {
                    "prefixed_ordinal_numeric_suffix",
                    "prefixed_ordinal_numeric_core",
                }
                and _spans_overlap(surface.span.start, surface.span.end, unit.span.start, unit.span.end)
            ):
                consumed.add((unit.span.start, unit.span.end))
                continue
            if (
                getattr(surface, "owner", None) == "time"
                and getattr(surface, "metadata", {}).get("compact_si_direction")
                is True
                and _spans_overlap(
                    surface.span.start, surface.span.end, unit.span.start, unit.span.end
                )
            ):
                consumed.add((unit.span.start, unit.span.end))
    return consumed


def _spans_overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return left_start < right_end and right_start < left_end
