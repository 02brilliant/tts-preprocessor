from __future__ import annotations

import re

from engine.span_engine.lexicon import LETTER_READINGS
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_number_text

_TAIL_MAX_LENGTH = 2
_K_HYPHEN_YEAR_CODE_DIGITS = 4
_CANDIDATE_RE = re.compile(
    rf"[A-Z]-?\d+(?:\.\d+)?[A-Z]{{0,{_TAIL_MAX_LENGTH}}}"
)
_FULL_RE = re.compile(rf"([A-Z])(-?)(\d+(?:\.\d+)?)([A-Z]{{0,{_TAIL_MAX_LENGTH}}})")
_MALFORMED_CANDIDATE_RE = re.compile(
    r"[A-Z](?:"
    r"\+-?\d+(?:\.\d+)?"
    r"|-[-+]\d+(?:\.\d+)?"
    r"|-?\.\d+"
    r"|-?0\d+(?:\.\d+)?"
    r"|-?\d+\."
    r"|-?\d+(?:\.\d+){2,}"
    r")"
)
_UNSAFE_DECIMAL_TAIL_RE = re.compile(
    r"[A-Z]-?\d+\.\d+(?=[A-Za-z_%~/&.+\-·ㆍ∙℃℉°º])\S*"
)

_ENGLISH_DIGIT_READINGS = {
    "1": "원",
    "2": "투",
    "3": "쓰리",
    "4": "포",
    "5": "파이브",
    "6": "식스",
    "7": "세븐",
    "8": "에이트",
    "9": "나인",
}
_LETTER_READINGS = {**LETTER_READINGS, "Z": "제트"}
_KOREAN_SUFFIXES = (
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "와",
    "과",
    "도",
    "로",
    "으로",
    "에",
    "에서",
    "부터",
    "까지",
    "입니다",
)


def scan_single_letter_alnum_code_candidates(
    raw_text: str,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for match in _CANDIDATE_RE.finditer(raw_text):
        raw = match.group(0)
        if not _safe_boundary(raw_text, match.start(), match.end()):
            continue
        reading = _reading(raw)
        if reading is None:
            continue
        span = SourceSpan(match.start(), match.end())
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="single_letter_alnum_code",
                surface_type="SINGLE_LETTER_ALNUM_CODE_SURFACE",
                reason="single_letter_uppercase_alnum_code_full_consume",
                metadata={"reading": reading},
            )
        )
    candidates.extend(_scan_malformed_preserve_candidates(raw_text))
    candidates.extend(_scan_unsafe_decimal_tail_preserve_candidates(raw_text))
    return candidates


def parse_single_letter_alnum_code_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "single_letter_alnum_code":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def _reading(raw: str) -> str | None:
    match = _FULL_RE.fullmatch(raw)
    if match is None:
        return None
    letter, hyphen, number, tail = match.groups()
    if _is_preserved_k_hyphen_year_code(letter, hyphen, number, tail):
        return None
    first_reading = _LETTER_READINGS.get(letter)
    if first_reading is None:
        return None
    if "." in number and tail:
        return None
    number_reading = numeric_code_number_reading(number)
    if number_reading is None:
        return None
    parts = [first_reading, number_reading]
    if tail:
        tail_reading = _tail_reading(tail)
        if tail_reading is None:
            return None
        parts.append(tail_reading)
    return " ".join(parts)


def _is_preserved_k_hyphen_year_code(
    letter: str, hyphen: str, number: str, tail: str
) -> bool:
    return (
        letter == "K"
        and hyphen == "-"
        and len(number) == _K_HYPHEN_YEAR_CODE_DIGITS
        and not tail
    )


def numeric_code_number_reading(number: str) -> str | None:
    if not number or not number.isascii():
        return None
    if number.isdigit() and len(number) == 1 and number != "0":
        return _ENGLISH_DIGIT_READINGS[number]
    return read_number_text(number)


def _tail_reading(tail: str) -> str | None:
    if not 1 <= len(tail) <= _TAIL_MAX_LENGTH:
        return None
    readings: list[str] = []
    for char in tail:
        reading = _LETTER_READINGS.get(char)
        if reading is None:
            return None
        readings.append(reading)
    return "".join(readings)


def _scan_malformed_preserve_candidates(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for match in _MALFORMED_CANDIDATE_RE.finditer(raw_text):
        if not _safe_boundary(raw_text, match.start(), match.end()):
            continue
        span = SourceSpan(match.start(), match.end())
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="preserve",
                surface_type="MALFORMED_SINGLE_LETTER_NUMERIC_CODE_PRESERVE",
                reason="malformed_single_letter_numeric_code_blocks_partial_fallback",
            )
        )
    return candidates


def _scan_unsafe_decimal_tail_preserve_candidates(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for match in _UNSAFE_DECIMAL_TAIL_RE.finditer(raw_text):
        if not _safe_preserve_start(raw_text, match.start()):
            continue
        span = SourceSpan(match.start(), match.end())
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="preserve",
                surface_type="UNSAFE_SINGLE_LETTER_DECIMAL_CODE_PRESERVE",
                reason="unsafe_single_letter_decimal_tail_blocks_partial_fallback",
            )
        )
    return candidates


def _safe_preserve_start(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char is None:
        return True
    return not _is_code_identifier_char(prev_char)


def _safe_boundary(raw_text: str, start: int, end: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    next_char = raw_text[end] if end < len(raw_text) else None
    if _has_previous_uppercase_context_token(raw_text, start):
        return False
    if prev_char is not None and _is_code_identifier_char(prev_char):
        return False
    if next_char in {",", "，"} and end + 1 < len(raw_text) and raw_text[end + 1].isdigit():
        return False
    if next_char is not None and "\uac00" <= next_char <= "\ud7a3":
        raw = raw_text[start:end]
        if "-" not in raw and not raw[-1].isalpha():
            return False
        return raw_text.startswith(_KOREAN_SUFFIXES, end)
    if next_char is not None and _is_unsafe_tail(next_char):
        return False
    return True


def _is_unsafe_tail(char: str) -> bool:
    if char.isascii() and char.isalnum():
        return True
    if "\u3130" <= char <= "\u318f":
        return True
    return char in {"_", "-", "/", ".", "%", "~", "∼", "&", "·", "ㆍ", "∙", "℃", "℉", "°", "º"}


def _has_previous_uppercase_context_token(raw_text: str, start: int) -> bool:
    prefix = raw_text[:start].rstrip()
    if not prefix:
        return False
    index = len(prefix) - 1
    while index >= 0 and prefix[index].isascii() and prefix[index].isalpha():
        index -= 1
    previous = prefix[index + 1 :]
    if len(previous) < 2 or not previous.isupper():
        return False
    if index >= 0 and not prefix[index].isspace():
        return False
    return True


def _is_code_identifier_char(char: str) -> bool:
    if char.isascii() and char.isalnum():
        return True
    if "\uac00" <= char <= "\ud7a3" or "\u3130" <= char <= "\u318f":
        return True
    return char in {"_", "-", "/", ".", "&", "·", "ㆍ", "∙"}


__all__ = [
    "numeric_code_number_reading",
    "parse_single_letter_alnum_code_candidate",
    "scan_single_letter_alnum_code_candidates",
]
