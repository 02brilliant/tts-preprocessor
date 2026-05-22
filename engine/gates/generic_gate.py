from __future__ import annotations

import re
from typing import Protocol

from .event_gate import EVENT_KEYWORD_WHITELIST
from .models import GateDecision, allow, deny


class TokenLike(Protocol):
    text: str
    start: int
    end: int


class RuleContextLike(Protocol):
    tokens: list[TokenLike]


SLASH_FRACTION_RE = re.compile(r"\d+/\d+")
SLASH_DATE_RE = re.compile(r"\d{4}/\d{1,2}/\d{1,2}")
SLASH_UNIT_RE = re.compile(r"[A-Za-z]{1,4}/[A-Za-z]{1,4}")
SLASH_OR_RE = re.compile(r"[^/\d\s]+/[^/\d\s]+")
WHITESPACE_SEARCH_RE = re.compile(r"\s")
NORMALIZED_EVENT_KEYWORDS = {re.sub(r"\s+", "", keyword) for keyword in EVENT_KEYWORD_WHITELIST}


def evaluate_decimal_context(
    *,
    candidate: str,
    text: str,
    start: int,
    end: int,
    ctx: RuleContextLike | None,
    **_: object,
) -> GateDecision:
    del candidate, ctx
    if start > 0 and text[start - 1] in (".", "#", "£", "$", "€", "₩", "￦", "¥", "￥"):
        return deny("preceding punctuation blocks decimal parse")
    if end < len(text) and text[end] == ".":
        return deny("trailing dot chain blocks decimal parse")
    if start > 0 and text[start - 1].lower() == "v":
        return deny("version-like prefix blocks decimal parse")
    if start > 0 and text[start - 1].isalpha():
        return deny("alphabetic attachment on the left blocks decimal parse")
    if end < len(text) and text[end].isalpha():
        return deny("alphabetic attachment on the right blocks decimal parse")

    right_context = text[end:].lstrip()
    normalized_right = re.sub(r"\s+", "", right_context)
    if any(normalized_right.startswith(keyword) for keyword in NORMALIZED_EVENT_KEYWORDS):
        return deny("immediate event keyword adjacency preserves dotted form")

    word_start = start
    while word_start > 0 and not text[word_start - 1].isspace():
        word_start -= 1
    word_end = end
    while word_end < len(text) and not text[word_end].isspace():
        word_end += 1
    surrounding_word = text[word_start:word_end]
    if looks_like_url_or_path(surrounding_word):
        return deny("url or path-like token blocks decimal parse")
    return allow("decimal context is safe")


def evaluate_unit_context(
    *,
    candidate: str,
    text: str,
    end: int,
    ctx: RuleContextLike | None,
    **_: object,
) -> GateDecision:
    del candidate

    def _is_ascii_alnum(char: str) -> bool:
        return char.isascii() and char.isalnum()

    def _has_trailing_slash_alpha(start_index: int) -> bool:
        return (
            start_index + 1 < len(text)
            and text[start_index] == "/"
            and text[start_index + 1].isascii()
            and text[start_index + 1].isalpha()
        )

    if end < len(text) and _has_trailing_slash_alpha(end):
        return deny("invalid slash tail blocks unit parse")

    if ctx is None:
        if end < len(text) and _is_ascii_alnum(text[end]):
            return deny("attached ascii alnum tail blocks unit parse")
        return allow("unit boundary is safe")

    next_token = None
    for token in ctx.tokens:
        if token.start >= end and not token.text.isspace():
            next_token = token
            break
    if next_token is not None and next_token.start == end and next_token.text and _is_ascii_alnum(next_token.text[0]):
        return deny("next token starts with attached ascii alnum")
    return allow("unit boundary is safe")


def evaluate_exact_text(
    *,
    start: int,
    end: int,
    text: str,
    **_: object,
) -> GateDecision:
    if start == 0 and end == len(text):
        return allow("candidate consumes the whole input")
    return deny("candidate must consume the whole input")


def evaluate_no_preceding_ascii_alpha(
    *,
    text: str,
    start: int,
    **_: object,
) -> GateDecision:
    index = start - 1
    while index >= 0 and text[index].isspace():
        index -= 1
    if index < 0:
        return allow("no preceding token")
    if text[index].isascii() and text[index].isalpha():
        return deny("preceding ascii alpha blocks special prefix parse")
    return allow("no preceding ascii alpha")


def evaluate_slash_date_context(
    *,
    candidate: str,
    **_: object,
) -> GateDecision:
    context = classify_slash_context(candidate)
    if context == "date":
        return allow("slash token classified as date")
    return deny("slash token is not classified as date", context=context)


def evaluate_slash_fraction_context(
    *,
    candidate: str,
    **_: object,
) -> GateDecision:
    context = classify_slash_context(candidate)
    if context == "fraction":
        return allow("slash token classified as fraction")
    return deny("slash token is not classified as fraction", context=context)


def classify_slash_context(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return "url"
    if SLASH_FRACTION_RE.fullmatch(stripped):
        return "fraction"
    if SLASH_DATE_RE.fullmatch(stripped):
        return "date"
    if SLASH_UNIT_RE.fullmatch(stripped):
        return "unit"
    if SLASH_OR_RE.fullmatch(stripped):
        return "or"
    return "unknown"


def looks_like_url_or_path(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if "://" in stripped:
        return True
    if stripped.startswith(("/", "./", "../")):
        return True
    if stripped.count("/") >= 2 and not WHITESPACE_SEARCH_RE.search(stripped):
        return True
    return False
