from __future__ import annotations

import re


_NEWLINE_RUN_RE = re.compile(r"(?:\r\n|\n|\r)+")
_CODE_FENCE_RE = re.compile(r"```[^\r\n]*(?:\r?\n)(?:.|\r|\n)*?```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def split_paragraph_units(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split already-normalized TTS text into paragraph chunks.

    Newline runs outside code fences and JSON-like objects are treated as
    paragraph separators and returned exactly so they can be restored.
    """

    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not text or not _NEWLINE_RUN_RE.search(text):
        return (text,), ()

    protected = _protected_ranges(text)
    chunks: list[str] = []
    separators: list[str] = []
    cursor = 0
    for match in _NEWLINE_RUN_RE.finditer(text):
        start, end = match.span()
        if any(range_start <= start < range_end for range_start, range_end in protected):
            continue
        chunks.append(text[cursor:start])
        separators.append(match.group(0))
        cursor = end
    chunks.append(text[cursor:])
    return tuple(chunks), tuple(separators)


def join_paragraph_units(
    chunks: tuple[str, ...],
    separators: tuple[str, ...],
) -> str:
    if len(chunks) != len(separators) + 1:
        raise ValueError("paragraph chunks and separators are misaligned.")
    if not separators:
        return chunks[0]
    parts = [chunks[0]]
    for separator, chunk in zip(separators, chunks[1:], strict=True):
        parts.append(separator)
        parts.append(chunk)
    return "".join(parts)


def _protected_ranges(text: str) -> tuple[tuple[int, int], ...]:
    ranges = [match.span() for match in _CODE_FENCE_RE.finditer(text)]
    ranges.extend(
        match.span()
        for match in _JSON_OBJECT_RE.finditer(text)
        if "\n" in match.group(0) and ":" in match.group(0)
    )
    return tuple(ranges)
