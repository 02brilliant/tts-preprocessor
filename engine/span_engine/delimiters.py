from __future__ import annotations

COLON_LIKE_DELIMITERS = frozenset({":", "："})
RANGE_LIKE_DELIMITERS = frozenset({"-", "–", "~", "～"})
TILDE_LIKE_DELIMITERS = frozenset({"~", "～", "∼", "〜"})


def is_colon_like(ch: str) -> bool:
    if not isinstance(ch, str):
        raise TypeError("ch must be str")
    return ch in COLON_LIKE_DELIMITERS


def is_range_like(ch: str) -> bool:
    if not isinstance(ch, str):
        raise TypeError("ch must be str")
    return ch in RANGE_LIKE_DELIMITERS


def is_tilde_like(ch: str) -> bool:
    if not isinstance(ch, str):
        raise TypeError("ch must be str")
    return ch in TILDE_LIKE_DELIMITERS


__all__ = [
    "COLON_LIKE_DELIMITERS",
    "RANGE_LIKE_DELIMITERS",
    "TILDE_LIKE_DELIMITERS",
    "is_colon_like",
    "is_range_like",
    "is_tilde_like",
]
