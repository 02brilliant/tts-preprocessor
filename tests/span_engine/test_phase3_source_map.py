from __future__ import annotations

import pytest

from engine.span_engine import SourceChar
from engine.span_engine.source_map import build_source_map


SOURCE_MAP_CASES = [
    "",
    "abc",
    "가나다",
    "A가😀B",
    "a\u200bb",
    "㎡㎏℃",
    "ㄱㄴㄷ",
    "[[K:사용자입력]]",
    "{{S:사용자입력}}",
]


@pytest.mark.parametrize("raw_text", SOURCE_MAP_CASES)
def test_build_source_map_preserves_every_python_code_point(raw_text: str) -> None:
    source_chars = build_source_map(raw_text)

    assert "".join(ch.char for ch in source_chars) == raw_text
    assert [ch.index for ch in source_chars] == list(range(len(raw_text)))


def test_build_source_map_empty_string() -> None:
    assert build_source_map("") == []


def test_build_source_map_tracks_hangul_and_emoji_indexes() -> None:
    assert build_source_map("A가😀B") == [
        SourceChar("A", 0),
        SourceChar("가", 1),
        SourceChar("😀", 2),
        SourceChar("B", 3),
    ]


@pytest.mark.parametrize("value", [None, 123, b"bytes"])
def test_build_source_map_rejects_non_str_input(value: object) -> None:
    with pytest.raises(TypeError):
        build_source_map(value)  # type: ignore[arg-type]
