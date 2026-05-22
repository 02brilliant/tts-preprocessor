from __future__ import annotations

from engine.span_engine.models import SourceChar, SourceSpan, SpanToken
from engine.span_engine.source_map import build_source_map

BOUNDARY_CHARS = frozenset("[](){}:|")
PUNCT_LOCK_CHARS = frozenset(".,!?")


def _is_modern_hangul_syllable(char: str) -> bool:
    return "\uac00" <= char <= "\ud7a3"


def _is_punct_lock_position(raw_text: str, index: int) -> bool:
    return (
        raw_text[index] in PUNCT_LOCK_CHARS
        and index > 0
        and _is_modern_hangul_syllable(raw_text[index - 1])
    )


def _validate_source_chars(raw_text: str, source_chars: list[SourceChar]) -> None:
    if not isinstance(source_chars, list):
        raise TypeError("source_chars must be list[SourceChar]")
    if len(source_chars) != len(raw_text):
        raise ValueError("source_chars must cover raw_text")
    for index, source_char in enumerate(source_chars):
        if not isinstance(source_char, SourceChar):
            raise TypeError("source_chars must contain SourceChar")
        if source_char.index != index or source_char.char != raw_text[index]:
            raise ValueError("source_chars must match raw_text code point indexes")


def tokenize_immutable_spans(
    raw_text: str, source_chars: list[SourceChar] | None = None
) -> list[SpanToken]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if source_chars is None:
        source_chars = build_source_map(raw_text)
    else:
        _validate_source_chars(raw_text, source_chars)

    tokens: list[SpanToken] = []
    i = 0
    while i < len(raw_text):
        char = raw_text[i]

        if _is_modern_hangul_syllable(char):
            start = i
            while i < len(raw_text) and _is_modern_hangul_syllable(raw_text[i]):
                i += 1
            tokens.append(
                SpanToken(
                    kind="KOREAN_LITERAL",
                    raw=raw_text[start:i],
                    span=SourceSpan(start, i),
                    immutable=True,
                )
            )
            continue

        if char.isspace():
            start = i
            while i < len(raw_text) and raw_text[i].isspace():
                i += 1
            tokens.append(
                SpanToken(
                    kind="SPACE_LOCK",
                    raw=raw_text[start:i],
                    span=SourceSpan(start, i),
                    immutable=True,
                )
            )
            continue

        if _is_punct_lock_position(raw_text, i):
            tokens.append(
                SpanToken(
                    kind="PUNCT_LOCK",
                    raw=char,
                    span=SourceSpan(i, i + 1),
                    immutable=True,
                )
            )
            i += 1
            continue

        if char in BOUNDARY_CHARS:
            tokens.append(
                SpanToken(
                    kind="BOUNDARY_LITERAL",
                    raw=char,
                    span=SourceSpan(i, i + 1),
                )
            )
            i += 1
            continue

        start = i
        while i < len(raw_text):
            current = raw_text[i]
            if (
                _is_modern_hangul_syllable(current)
                or current.isspace()
                or current in BOUNDARY_CHARS
                or _is_punct_lock_position(raw_text, i)
            ):
                break
            i += 1
        tokens.append(
            SpanToken(
                kind="PLAIN",
                raw=raw_text[start:i],
                span=SourceSpan(start, i),
            )
        )

    validate_token_coverage(raw_text, tokens)
    return tokens


def validate_token_coverage(raw_text: str, tokens: list[SpanToken]) -> None:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(tokens, list):
        raise TypeError("tokens must be list[SpanToken]")

    cursor = 0
    for token in tokens:
        if not isinstance(token, SpanToken):
            raise TypeError("tokens must contain SpanToken")
        if token.span.start != cursor:
            raise ValueError("token spans must cover raw_text without gaps")
        if token.span.end < token.span.start:
            raise ValueError("token span end must be >= start")
        if raw_text[token.span.start : token.span.end] != token.raw:
            raise ValueError("token raw must match raw_text slice")
        cursor = token.span.end
    if cursor != len(raw_text):
        raise ValueError("token spans must cover all raw_text")
