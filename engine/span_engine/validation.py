from __future__ import annotations

from collections import defaultdict

from engine.span_engine.models import (
    RenderPiece,
    ShadowUnit,
    ValidationLog,
    ValidationResult,
)

EXPECTED_PROVENANCE_BY_SHADOW_KIND = {
    "KOREAN_LITERAL": "ORIGINAL_KOREAN",
    "KOREAN_SPACE": "ORIGINAL_SPACE",
    "KOREAN_PUNCT": "ORIGINAL_PUNCT",
    "PARTICLE_LITERAL": "ORIGINAL_KOREAN",
}


def expected_provenance_for_shadow_kind(kind: str) -> str:
    try:
        return EXPECTED_PROVENANCE_BY_SHADOW_KIND[kind]
    except KeyError as exc:
        raise ValueError(f"unsupported shadow kind: {kind!r}") from exc


def _span_key(piece: RenderPiece) -> tuple[int, int] | None:
    if piece.source_span is None:
        return None
    return (piece.source_span.start, piece.source_span.end)


def _index_pieces_by_span_and_provenance(
    pieces: list[RenderPiece],
) -> dict[tuple[int, int, str], list[RenderPiece]]:
    by_key: dict[tuple[int, int, str], list[RenderPiece]] = defaultdict(list)
    for piece in pieces:
        span_key = _span_key(piece)
        if span_key is None:
            continue
        by_key[(span_key[0], span_key[1], piece.provenance)].append(piece)
    return by_key


def _validate_consumed_spans(name: str, spans: object) -> None:
    if not isinstance(spans, set):
        raise TypeError(f"{name} must be set or None")
    for span in spans:
        if (
            not isinstance(span, tuple)
            or len(span) != 2
            or not all(isinstance(value, int) for value in span)
        ):
            raise TypeError(f"{name} must contain (int, int) tuples")


def validate_shadow(
    pieces: list[RenderPiece],
    shadow: list[ShadowUnit],
    consumed_particle_spans: set[tuple[int, int]] | None = None,
    consumed_shadow_spans: set[tuple[int, int]] | None = None,
) -> ValidationResult:
    if not isinstance(pieces, list):
        raise TypeError("pieces must be list[RenderPiece]")
    if not isinstance(shadow, list):
        raise TypeError("shadow must be list[ShadowUnit]")
    if consumed_particle_spans is None:
        consumed_particle_spans = set()
    if consumed_shadow_spans is None:
        consumed_shadow_spans = set()
    _validate_consumed_spans("consumed_particle_spans", consumed_particle_spans)
    _validate_consumed_spans("consumed_shadow_spans", consumed_shadow_spans)
    for piece in pieces:
        if not isinstance(piece, RenderPiece):
            raise TypeError("pieces must contain RenderPiece")
    for unit in shadow:
        if not isinstance(unit, ShadowUnit):
            raise TypeError("shadow must contain ShadowUnit")

    by_key = _index_pieces_by_span_and_provenance(pieces)

    logs: list[ValidationLog] = []
    duplicate_keys = {
        key for key, matching_pieces in by_key.items() if len(matching_pieces) > 1
    }
    for start, end, provenance in sorted(duplicate_keys):
        if provenance.startswith("ORIGINAL_"):
            logs.append(
                ValidationLog(
                    kind="DUPLICATE_ORIGINAL_PIECE",
                    passed=False,
                    span=pieces[0].source_span,
                    reason="duplicate_original_piece",
                    metadata={"key": [start, end, provenance]},
                )
            )

    for unit in shadow:
        expected_provenance = expected_provenance_for_shadow_kind(unit.kind)
        key = (unit.span.start, unit.span.end, expected_provenance)
        matching = by_key.get(key, [])

        if matching:
            piece = matching[0]
            if piece.text == unit.raw:
                logs.append(
                    ValidationLog(
                        kind=unit.kind,
                        passed=True,
                        expected=unit.raw,
                        actual=piece.text,
                        span=unit.span,
                        reason="matched_original_piece",
                    )
                )
            else:
                logs.append(
                    ValidationLog(
                        kind=unit.kind,
                        passed=False,
                        expected=unit.raw,
                        actual=piece.text,
                        span=unit.span,
                        reason="original_text_mismatch",
                    )
                )
            continue

        if (unit.span.start, unit.span.end) in consumed_particle_spans:
            logs.append(
                ValidationLog(
                    kind=unit.kind,
                    passed=True,
                    expected=unit.raw,
                    actual="PARTICLE_EXCEPTION_CONSUMED",
                    span=unit.span,
                    reason="particle_exception_consumed",
                    metadata={"marker": "PARTICLE_EXCEPTION_CONSUMED"},
                )
            )
            continue

        if (unit.span.start, unit.span.end) in consumed_shadow_spans:
            logs.append(
                ValidationLog(
                    kind=unit.kind,
                    passed=True,
                    expected=unit.raw,
                    actual="SURFACE_INTERNAL_CONSUMED",
                    span=unit.span,
                    reason="surface_internal_consumed",
                    metadata={"marker": "SURFACE_INTERNAL_CONSUMED"},
                )
            )
            continue

        same_span = [
            piece
            for piece in pieces
            if piece.source_span is not None
            and piece.source_span.start == unit.span.start
            and piece.source_span.end == unit.span.end
        ]
        if same_span:
            piece = same_span[0]
            logs.append(
                ValidationLog(
                    kind=unit.kind,
                    passed=False,
                    expected=unit.raw,
                    actual=piece.text,
                    span=unit.span,
                    reason="provenance_mismatch",
                    metadata={
                        "expected_provenance": expected_provenance,
                        "actual_provenance": piece.provenance,
                    },
                )
            )
            continue

        same_text_expected_provenance = [
            piece
            for piece in pieces
            if piece.provenance == expected_provenance and piece.text == unit.raw
        ]
        if same_text_expected_provenance:
            piece = same_text_expected_provenance[0]
            logs.append(
                ValidationLog(
                    kind=unit.kind,
                    passed=False,
                    expected=unit.raw,
                    actual=piece.text,
                    span=unit.span,
                    reason="source_span_mismatch",
                    metadata={
                        "actual_span": (
                            [
                                piece.source_span.start,
                                piece.source_span.end,
                            ]
                            if piece.source_span is not None
                            else None
                        )
                    },
                )
            )
            continue

        logs.append(
            ValidationLog(
                kind=unit.kind,
                passed=False,
                expected=unit.raw,
                actual=None,
                span=unit.span,
                reason="missing_original_piece",
            )
        )

    return ValidationResult(passed=all(log.passed for log in logs), logs=logs)
