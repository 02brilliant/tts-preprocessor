from __future__ import annotations

from engine.span_engine.models import SourceSpan, SurfaceCandidate

DICTIONARY_READINGS: dict[str, str] = {
    "AI": "에이아이",
    "FTA": "에프티에이",
    "MFN": "엠에프엔",
    "KOSPI": "코스피",
    "KOSDAQ": "코스닥",
    "TTS": "티티에스",
    "API": "에이피아이",
    "CPU": "씨피유",
    "GPU": "지피유",
    "PDF": "피디에프",
    "JSON": "제이슨",
    "URL": "유알엘",
    "K-POP": "케이팝",
    "4K": "포케이",
    "KBS": "케이비에스",
    "LLM": "엘엘엠",
    "OECD": "오이씨디",
    "WHO": "더블유에이치오",
}

LEXICAL_COMPOUND_READINGS: dict[str, str] = {
    "ISO·IEC": "아이에스오·아이이씨",
}
_K_HANGUL_PREFIX = "K-"
_K_HANGUL_UNSAFE_TAIL_CHARS = frozenset("-_/.")

LETTER_READINGS: dict[str, str] = {
    "A": "에이",
    "B": "비",
    "C": "씨",
    "D": "디",
    "E": "이",
    "F": "에프",
    "G": "지",
    "H": "에이치",
    "I": "아이",
    "J": "제이",
    "K": "케이",
    "L": "엘",
    "M": "엠",
    "N": "엔",
    "O": "오",
    "P": "피",
    "Q": "큐",
    "R": "알",
    "S": "에스",
    "T": "티",
    "U": "유",
    "V": "브이",
    "W": "더블유",
    "X": "엑스",
    "Y": "와이",
    "Z": "지",
}


def dictionary_reading(raw: str) -> str | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    return DICTIONARY_READINGS.get(raw)


def lexical_compound_reading(raw: str) -> str | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    return LEXICAL_COMPOUND_READINGS.get(raw)


def k_hangul_lexical_reading(raw: str) -> str | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    if not raw.startswith(_K_HANGUL_PREFIX):
        return None
    hangul = raw[len(_K_HANGUL_PREFIX) :]
    if not hangul or not all(_is_complete_hangul(char) for char in hangul):
        return None
    return f"케이{hangul}"


def spell_uppercase_acronym(raw: str) -> str:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    return "".join(LETTER_READINGS[char] for char in raw)


def scan_lexical_compound_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for surface, reading in LEXICAL_COMPOUND_READINGS.items():
        start = raw_text.find(surface)
        while start != -1:
            end = start + len(surface)
            if _safe_fixed_surface_boundary(raw_text, start, end):
                span = SourceSpan(start, end)
                candidates.append(
                    SurfaceCandidate(
                        core_span=span,
                        full_span=span,
                        owner="lexical_compound",
                        surface_type="LEXICAL_COMPOUND_SURFACE",
                        reason="fixed_lexical_compound_match",
                        metadata={"reading": reading},
                    )
                )
            start = raw_text.find(surface, start + 1)
    return sorted(candidates, key=lambda candidate: candidate.core_span.start)


def scan_k_hangul_lexical_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    start = raw_text.find(_K_HANGUL_PREFIX)
    while start != -1:
        hangul_start = start + len(_K_HANGUL_PREFIX)
        if not _safe_k_hangul_left_boundary(raw_text, start):
            start = raw_text.find(_K_HANGUL_PREFIX, start + 1)
            continue
        if hangul_start >= len(raw_text) or not _is_complete_hangul(raw_text[hangul_start]):
            start = raw_text.find(_K_HANGUL_PREFIX, start + 1)
            continue
        end = hangul_start
        while end < len(raw_text) and _is_complete_hangul(raw_text[end]):
            end += 1
        if _has_k_hangul_unsafe_tail(raw_text, end):
            start = raw_text.find(_K_HANGUL_PREFIX, start + 1)
            continue
        span = SourceSpan(start, end)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="k_hangul_lexical",
                surface_type="K_HANGUL_LEXICAL_SURFACE",
                reason="k_hangul_lexical_prefix_full_consume",
            )
        )
        start = raw_text.find(_K_HANGUL_PREFIX, start + 1)
    return candidates


def _safe_fixed_surface_boundary(raw_text: str, start: int, end: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    next_char = raw_text[end] if end < len(raw_text) else None
    if prev_char is not None and _is_identifier_neighbor(prev_char):
        return False
    if next_char is not None and "\uac00" <= next_char <= "\ud7a3":
        return _starts_with_trailing_particle(raw_text, end)
    if next_char is not None and _is_identifier_neighbor(next_char):
        return False
    return True


def _starts_with_trailing_particle(raw_text: str, index: int) -> bool:
    return any(
        raw_text.startswith(particle, index)
        for particle in ("은", "는", "이", "가", "을", "를", "와", "과")
    )


def _safe_k_hangul_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    prev_char = raw_text[start - 1]
    if prev_char.isspace():
        return True
    if _is_identifier_neighbor(prev_char):
        return False
    return True


def _has_k_hangul_unsafe_tail(raw_text: str, end: int) -> bool:
    if end >= len(raw_text):
        return False
    next_char = raw_text[end]
    if next_char.isascii() and next_char.isalnum():
        return True
    return next_char in _K_HANGUL_UNSAFE_TAIL_CHARS


def _is_complete_hangul(char: str) -> bool:
    return "\uac00" <= char <= "\ud7a3"


def _is_identifier_neighbor(char: str) -> bool:
    if char.isascii() and char.isalnum():
        return True
    if "\uac00" <= char <= "\ud7a3" or "\u3130" <= char <= "\u318f":
        return True
    return char in {"-", "_", "/"}


__all__ = [
    "DICTIONARY_READINGS",
    "LETTER_READINGS",
    "LEXICAL_COMPOUND_READINGS",
    "dictionary_reading",
    "k_hangul_lexical_reading",
    "lexical_compound_reading",
    "scan_k_hangul_lexical_candidates",
    "scan_lexical_compound_candidates",
    "spell_uppercase_acronym",
]
