from __future__ import annotations

from dataclasses import dataclass, field

from engine.span_engine.models import RenderPiece, SourceSpan, TraceLogEntry

A1_PARTICLES = frozenset({"은", "는", "을", "를", "으로"})
A2_NOOP_PARTICLES = frozenset({"이"})
RISKY_PARTICLES = frozenset({"가", "로", "과", "와", "도"})
PARTICLE_EXCEPTION_CONSUMED = "PARTICLE_EXCEPTION_CONSUMED"
JONGSEONG_RIEUL_INDEX = 8


@dataclass
class ParticleExceptionResult:
    pieces: list[RenderPiece]
    consumed_spans: set[tuple[int, int]] = field(default_factory=set)
    logs: list[TraceLogEntry] = field(default_factory=list)


def final_hangul_syllable(text: str) -> str | None:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    stripped = text.rstrip()
    if not stripped:
        return None
    char = stripped[-1]
    if _is_modern_hangul_syllable(char):
        return char
    return None


def jongseong_index(ch: str) -> int:
    if not isinstance(ch, str):
        raise TypeError("ch must be str")
    if len(ch) != 1 or not _is_modern_hangul_syllable(ch):
        raise ValueError("ch must be a single modern Hangul syllable")
    return (ord(ch) - 0xAC00) % 28


def has_jongseong(ch: str) -> bool:
    return jongseong_index(ch) != 0


def choose_safe_particle(reading: str, particle: str) -> str | None:
    if not isinstance(reading, str):
        raise TypeError("reading must be str")
    if not isinstance(particle, str):
        raise TypeError("particle must be str")
    if particle in A2_NOOP_PARTICLES or particle in RISKY_PARTICLES:
        return None

    tail = final_hangul_syllable(reading)
    if tail is None:
        return None
    tail_has_jongseong = has_jongseong(tail)
    tail_jongseong = jongseong_index(tail)

    if particle in {"은", "는"}:
        return "은" if tail_has_jongseong else "는"
    if particle in {"을", "를"}:
        return "을" if tail_has_jongseong else "를"
    if particle == "으로":
        if not tail_has_jongseong or tail_jongseong == JONGSEONG_RIEUL_INDEX:
            return "로"
        return "으로"
    return None


def apply_safe_post_surface_particle_exception(
    pieces: list[RenderPiece],
) -> ParticleExceptionResult:
    if not isinstance(pieces, list):
        raise TypeError("pieces must be list[RenderPiece]")
    for piece in pieces:
        if not isinstance(piece, RenderPiece):
            raise TypeError("pieces must contain RenderPiece")

    output: list[RenderPiece] = []
    consumed_spans: set[tuple[int, int]] = set()
    logs: list[TraceLogEntry] = []

    index = 0
    while index < len(pieces):
        current = pieces[index]
        next_piece = pieces[index + 1] if index + 1 < len(pieces) else None

        if _is_generated_surface_before_particle(current, next_piece):
            particle = next_piece.text  # type: ignore[union-attr]
            if particle in A2_NOOP_PARTICLES:
                output.append(current)
                output.append(next_piece)  # type: ignore[arg-type]
                logs.append(_noop_log(current, next_piece))  # type: ignore[arg-type]
                index += 2
                continue

            generated_particle = choose_safe_particle(current.text, particle)
            if current.owner == "decimal" and particle == "으로":
                generated_particle = None
            if generated_particle is not None:
                output.append(current)
                output.append(
                    _generated_particle_piece(
                        current,
                        next_piece,  # type: ignore[arg-type]
                        generated_particle,
                    )
                )
                consumed_spans.add(_span_tuple(next_piece.source_span))  # type: ignore[union-attr]
                logs.append(
                    _replacement_log(
                        current,
                        next_piece,  # type: ignore[arg-type]
                        generated_particle,
                    )
                )
                index += 2
                continue

        output.append(current)
        index += 1

    return ParticleExceptionResult(output, consumed_spans, logs)


def _is_generated_surface_before_particle(
    current: RenderPiece, next_piece: RenderPiece | None
) -> bool:
    return (
        current.provenance == "GENERATED_READING"
        and current.owner is not None
        and next_piece is not None
        and next_piece.provenance == "ORIGINAL_KOREAN"
        and next_piece.source_span is not None
        and next_piece.text in (A1_PARTICLES | A2_NOOP_PARTICLES | RISKY_PARTICLES)
    )


def _generated_particle_piece(
    surface_piece: RenderPiece, particle_piece: RenderPiece, generated_particle: str
) -> RenderPiece:
    return RenderPiece(
        text=generated_particle,
        provenance="GENERATED_PARTICLE",
        source_span=particle_piece.source_span,
        owner=surface_piece.owner,
        metadata={
            "original_particle": particle_piece.text,
            "original_span": particle_piece.source_span,
            "surface_span": surface_piece.source_span,
            "marker": PARTICLE_EXCEPTION_CONSUMED,
        },
    )


def _replacement_log(
    surface_piece: RenderPiece, particle_piece: RenderPiece, generated_particle: str
) -> TraceLogEntry:
    return TraceLogEntry(
        stage="particle_exception",
        event="safe_particle_replaced",
        span=particle_piece.source_span,
        raw=particle_piece.text,
        owner=surface_piece.owner,
        decision="applied",
        reason="safe_post_surface_particle_exception",
        action="replace_particle",
        expected=particle_piece.text,
        actual=generated_particle,
        metadata={
            "marker": PARTICLE_EXCEPTION_CONSUMED,
            "original_particle": particle_piece.text,
            "generated_particle": generated_particle,
            "surface_span": surface_piece.source_span,
        },
    )


def _noop_log(surface_piece: RenderPiece, particle_piece: RenderPiece) -> TraceLogEntry:
    return TraceLogEntry(
        stage="particle_exception",
        event="safe_particle_noop",
        span=particle_piece.source_span,
        raw=particle_piece.text,
        owner=surface_piece.owner,
        decision="noop",
        reason="safe_post_surface_particle_exception_noop",
        action="preserve_particle",
        expected=particle_piece.text,
        actual=particle_piece.text,
        metadata={
            "original_particle": particle_piece.text,
            "surface_span": surface_piece.source_span,
        },
    )


def _span_tuple(span: SourceSpan | None) -> tuple[int, int]:
    if span is None:
        raise ValueError("particle source_span is required")
    return (span.start, span.end)


def _is_modern_hangul_syllable(char: str) -> bool:
    return "\uac00" <= char <= "\ud7a3"


__all__ = [
    "A1_PARTICLES",
    "A2_NOOP_PARTICLES",
    "PARTICLE_EXCEPTION_CONSUMED",
    "ParticleExceptionResult",
    "RISKY_PARTICLES",
    "apply_safe_post_surface_particle_exception",
    "choose_safe_particle",
    "final_hangul_syllable",
    "has_jongseong",
    "jongseong_index",
]
