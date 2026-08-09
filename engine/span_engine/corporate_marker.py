from __future__ import annotations

from engine.span_engine.models import SourceSpan, SurfaceCandidate


_CORPORATE_MARKER = "㈜"


def scan_corporate_marker_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for index, char in enumerate(raw_text):
        if char != _CORPORATE_MARKER:
            continue
        next_char = raw_text[index + 1] if index + 1 < len(raw_text) else None
        separator = " " if next_char is not None and _is_adjacent_word_char(next_char) else ""
        span = SourceSpan(index, index + 1)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="corporate_marker",
                surface_type="CORPORATE_MARKER_SURFACE",
                reason="corporate_marker_expand_with_word_separator",
                metadata={"reading": f"주식회사{separator}"},
            )
        )
    return candidates


def parse_corporate_marker_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "corporate_marker":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def _is_adjacent_word_char(char: str) -> bool:
    return (
        char.isascii() and char.isalpha()
    ) or "\uac00" <= char <= "\ud7a3"


__all__ = ["parse_corporate_marker_candidate", "scan_corporate_marker_candidates"]
