from __future__ import annotations

from typing import Any

from engine.span_engine.models import SourceChar


def build_source_map(raw_text: str) -> list[SourceChar]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    return [SourceChar(char=char, index=index) for index, char in enumerate(raw_text)]


def source_map_summary(raw_text: str, source_chars: list[SourceChar]) -> dict[str, Any]:
    return {
        "raw_length": len(raw_text),
        "codepoint_indexing": "python_str_code_point",
        "normalization_applied": False,
        "coverage_span": [0, len(raw_text)],
        "source_char_count": len(source_chars),
    }
