from __future__ import annotations

import re

from engine.span_engine.models import SourceSpan, SurfaceCandidate

_URL_RE = re.compile(r"(?<![A-Za-z0-9_.-])(?:https?://|www\.)[^\s,，]+")
_CURL_COMMAND_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])curl(?:\s+(?![가-힣])\S+)+"
)
_INLINE_JSON_OBJECT_RE = re.compile(r"(?<![A-Za-z0-9_])\{[^{}\n]*\}(?![A-Za-z0-9_])")
_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9_.%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9_.%+-])"
)
_DRIVE_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])[A-Za-z]:[\\/][^\s,，]+")
_ABSOLUTE_PATH_RE = re.compile(r"(?<!\S)(?:/|\\)[^\s,，]+(?:[\\/][^\s,，]+)+")
_RELATIVE_FILE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:[A-Za-z][A-Za-z0-9_.-]*[\\/])+[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,8}(?![A-Za-z0-9_.-])"
)
_RELATIVE_MULTI_SEGMENT_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])[A-Za-z][A-Za-z0-9_.-]*(?:[\\/][A-Za-z0-9_.-]+){2,}(?![A-Za-z0-9_.-])"
)
_IDENTIFIER_LIKE_RE = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+(?![A-Za-z0-9_])"
)
_VERSION_SIGNED_RANGE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"[Vv]-\d+(?:\.\d+)?[~～∼〜]-?\d+(?:\.\d+)?[A-Za-z가-힣%℃㎜㎝㎞㎎㎏㎖]*"
    r"(?![A-Za-z0-9_.-])"
)
_MATH_TERM = r"(?:[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?)"
_MATH_ASSIGNMENT_RE = re.compile(
    rf"(?<![A-Za-z0-9_])"
    rf"{_MATH_TERM}(?:\s*[+\-*/]\s*{_MATH_TERM})*"
    rf"\s*(?:==|>=|<=|\+=|-=|\*=|/=|=)\s*{_MATH_TERM}"
    rf"(?![A-Za-z0-9_])"
)
_PLUS_WORD_EXPRESSION_RE = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9_]*(?:\+[A-Za-z][A-Za-z0-9_]*)+(?![A-Za-z0-9_])"
)
_CPP_STYLE_RE = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9_]*\+\+\d*(?![A-Za-z0-9_])"
)
_MARKDOWN_CODE_FENCE_RE = re.compile(r"```[^\r\n]*(?:\r?\n)(?:.|\r|\n)*?```(?:\r?\n)?")
_INLINE_BACKTICK_RE = re.compile(r"(?<!`)`(?!`)[^`\r\n]+(?<!`)`(?!`)")
_SENTENCE_LIKE_RE = re.compile(r"[^.!?\n]+[.!?]")
_QUOTED_ENGLISH_PROSE_RE = re.compile(r'"[^"\n]*[A-Za-z][^"\n]*[.!?]"')
_ENGLISH_PROSE_WITH_PH_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"[A-Za-z][^가-힣\n]*?\bpH\s+\d+(?:\.\d+)?[^가-힣\n]*?"
    r"(?:[!?]|(?<!\d)\.(?!\d))"
)
_PH_ENGLISH_PROSE_RE = re.compile(
    r"(?<![A-Za-z0-9])pH\s+\d+(?:\.\d+)?[^가-힣\n]*?(?:[!?]|(?<!\d)\.(?!\d))"
)
_INLINE_ENGLISH_SENTENCE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z][^.!?\n가-힣\"]*[a-z][^.!?\n가-힣\"]*[.!?])"
)
_LOWERCASE_WORD_RE = re.compile(r"\b[A-Za-z]*[a-z][A-Za-z]*\b")


def scan_protected_literal_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    return [
        SurfaceCandidate(
            core_span=span,
            full_span=span,
            owner="preserve",
            surface_type="PROTECTED_LITERAL_SURFACE",
            reason="url_path_email_code_protection_claim",
        )
        for span in protected_literal_spans(raw_text)
    ]


def protected_literal_spans(text: str) -> list[SourceSpan]:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    spans: list[SourceSpan] = []
    for span in _markdown_code_spans(text):
        spans.append(span)
    for span in _quoted_english_prose_spans(text):
        if _overlaps_any(span, spans):
            continue
        spans.append(span)
    for span in _inline_english_prose_spans(text):
        if _overlaps_any(span, spans):
            continue
        spans.append(span)
    for span in _inline_non_korean_prose_spans(text):
        if _overlaps_any(span, spans):
            continue
        spans.append(span)
    for regex in (
        _CURL_COMMAND_RE,
        _INLINE_JSON_OBJECT_RE,
        _URL_RE,
        _EMAIL_RE,
        _DRIVE_PATH_RE,
        _ABSOLUTE_PATH_RE,
        _RELATIVE_FILE_PATH_RE,
        _RELATIVE_MULTI_SEGMENT_PATH_RE,
        _IDENTIFIER_LIKE_RE,
        _VERSION_SIGNED_RANGE_RE,
        _MATH_ASSIGNMENT_RE,
        _PLUS_WORD_EXPRESSION_RE,
        _CPP_STYLE_RE,
    ):
        for match in regex.finditer(text):
            span = SourceSpan(match.start(), match.end())
            if _overlaps_any(span, spans):
                continue
            spans.append(span)
    for span in json_like_string_value_spans(text):
        if _overlaps_any(span, spans):
            continue
        spans.append(span)
    return sorted(spans, key=lambda span: span.start)


def json_like_string_value_spans(text: str) -> list[SourceSpan]:
    """Return quoted string value spans inside narrow JSON-like containers."""
    if not isinstance(text, str):
        raise TypeError("text must be str")

    spans: list[SourceSpan] = []
    for container_start, container_end in _json_like_container_bounds(text):
        spans.extend(_json_string_value_spans_in_container(text, container_start, container_end))
    return sorted(spans, key=lambda span: span.start)


def _markdown_code_spans(text: str) -> list[SourceSpan]:
    spans: list[SourceSpan] = []
    for regex in (_MARKDOWN_CODE_FENCE_RE, _INLINE_BACKTICK_RE):
        for match in regex.finditer(text):
            span = SourceSpan(match.start(), match.end())
            if _overlaps_any(span, spans):
                continue
            spans.append(span)
    return sorted(spans, key=lambda span: span.start)


def _json_like_container_bounds(text: str) -> list[tuple[int, int]]:
    pairs = {"{": "}", "[": "]"}
    bounds: list[tuple[int, int]] = []
    index = 0
    while index < len(text):
        opener = text[index]
        closer = pairs.get(opener)
        if closer is None:
            index += 1
            continue

        end = _find_json_like_container_end(text, index, opener, closer)
        if end is None:
            index += 1
            continue

        raw = text[index : end + 1]
        if _looks_json_like_container(raw):
            bounds.append((index, end + 1))
            index = end + 1
            continue
        index += 1
    return bounds


def _find_json_like_container_end(
    text: str,
    start: int,
    opener: str,
    closer: str,
) -> int | None:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if char in "\r\n":
            return None
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == '"':
            quote = char
            continue
        if char == opener:
            depth += 1
            continue
        if char == closer:
            depth -= 1
            if depth == 0:
                return index
    return None


def _looks_json_like_container(raw: str) -> bool:
    stripped = raw.strip()
    if stripped.startswith("{"):
        return '":"' in stripped or '": "' in stripped or '":' in stripped
    if stripped.startswith("["):
        return '"' in stripped
    return False


def _json_string_value_spans_in_container(
    text: str,
    container_start: int,
    container_end: int,
) -> list[SourceSpan]:
    spans: list[SourceSpan] = []
    index = container_start + 1
    while index < container_end - 1:
        if text[index] != '"':
            index += 1
            continue

        string_end = _find_json_string_end(text, index, container_end)
        if string_end is None:
            break
        if _is_json_like_value_string(text, container_start, index, string_end):
            spans.append(SourceSpan(index, string_end + 1))
        index = string_end + 1
    return spans


def _find_json_string_end(text: str, start: int, limit: int) -> int | None:
    escaped = False
    for index in range(start + 1, limit):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return index
    return None


def _is_json_like_value_string(
    text: str,
    container_start: int,
    quote_start: int,
    quote_end: int,
) -> bool:
    cursor = quote_start - 1
    while cursor > container_start and text[cursor].isspace():
        cursor -= 1
    if cursor <= container_start:
        return text[container_start] == "["
    if text[cursor] == ":":
        return True
    if text[container_start] == "[" and text[cursor] in {"[", ","}:
        return True
    if text[container_start] == "{" and text[cursor] == ",":
        next_cursor = quote_end + 1
        while next_cursor < len(text) and text[next_cursor].isspace():
            next_cursor += 1
        return next_cursor >= len(text) or text[next_cursor] != ":"
    return False


def _quoted_english_prose_spans(text: str) -> list[SourceSpan]:
    if not any("\uac00" <= char <= "\ud7a3" for char in text):
        return []
    pairs = {'"': '"', "'": "'", "“": "”", "‘": "’"}
    spans: list[SourceSpan] = []
    for start, opener in enumerate(text):
        closer = pairs.get(opener)
        if closer is None:
            continue
        cursor = start + 1
        while True:
            end = text.find(closer, cursor)
            if end == -1:
                break
            raw = text[start : end + 1]
            if _is_quoted_english_prose(raw):
                span = SourceSpan(start, end + 1)
                if not _overlaps_any(span, spans):
                    spans.append(span)
                break
            cursor = end + 1
    return sorted(spans, key=lambda span: span.start)


def _inline_english_prose_spans(text: str) -> list[SourceSpan]:
    if not any("\uac00" <= char <= "\ud7a3" for char in text):
        return []
    spans: list[SourceSpan] = []
    for regex in (
        _QUOTED_ENGLISH_PROSE_RE,
        _ENGLISH_PROSE_WITH_PH_RE,
        _PH_ENGLISH_PROSE_RE,
        _INLINE_ENGLISH_SENTENCE_RE,
    ):
        for match in regex.finditer(text):
            raw = match.group()
            if not _is_inline_english_prose(raw):
                continue
            if (
                raw.endswith(".")
                and match.end() < len(text)
                and text[match.end()].isdigit()
            ):
                continue
            span = SourceSpan(match.start(), match.end())
            if _overlaps_any(span, spans):
                continue
            spans.append(span)
    return sorted(spans, key=lambda span: span.start)


def _inline_non_korean_prose_spans(text: str) -> list[SourceSpan]:
    spans: list[SourceSpan] = []
    for match in _SENTENCE_LIKE_RE.finditer(text):
        raw = match.group()
        stripped = raw.strip()
        if not any("\uac00" <= char <= "\ud7a3" for char in text):
            continue
        if not _is_inline_english_prose(stripped):
            continue
        spans.append(SourceSpan(match.start(), match.end()))
    return spans


def _is_quoted_english_prose(raw: str) -> bool:
    stripped = raw.strip().strip("\"'“”‘’`")
    if not stripped:
        return False
    if any("\uac00" <= char <= "\ud7a3" for char in stripped):
        return False
    if " " not in stripped:
        return False
    return len(_LOWERCASE_WORD_RE.findall(stripped)) >= 2


def _is_inline_english_prose(raw: str) -> bool:
    stripped = raw.strip().strip("\"'“”‘’")
    if not stripped:
        return False
    if "://" in stripped or "/" in stripped or "\\" in stripped or "@" in stripped:
        return False
    if any("\uac00" <= char <= "\ud7a3" for char in stripped):
        return False
    if " " not in stripped:
        return False
    return len(_LOWERCASE_WORD_RE.findall(stripped)) >= 2


def is_standalone_protected_literal(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    stripped = text.strip()
    if not stripped:
        return False
    spans = protected_literal_spans(stripped)
    return len(spans) == 1 and spans[0].start == 0 and spans[0].end == len(stripped)


def mask_protected_literals(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    chars = list(text)
    for span in protected_literal_spans(text):
        for index in range(span.start, span.end):
            chars[index] = " "
    return "".join(chars)


def _overlaps_any(span: SourceSpan, spans: list[SourceSpan]) -> bool:
    return any(span.start < existing.end and existing.start < span.end for existing in spans)


__all__ = [
    "is_standalone_protected_literal",
    "json_like_string_value_spans",
    "mask_protected_literals",
    "protected_literal_spans",
    "scan_protected_literal_candidates",
]
