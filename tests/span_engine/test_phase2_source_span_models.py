from __future__ import annotations

import pytest

from engine.span_engine import SourceChar, SourceSpan


def test_source_span_length_uses_python_code_point_indexes() -> None:
    assert SourceSpan(0, 0).length == 0
    assert SourceSpan(0, 1).length == 1
    assert SourceSpan(2, 5).length == 3


def test_source_span_tracks_emoji_and_hangul_as_python_str_code_points() -> None:
    raw_text = "A가😀B"

    assert len(raw_text) == 4
    assert raw_text[SourceSpan(0, 1).start : SourceSpan(0, 1).end] == "A"
    assert raw_text[SourceSpan(1, 2).start : SourceSpan(1, 2).end] == "가"
    assert raw_text[SourceSpan(2, 3).start : SourceSpan(2, 3).end] == "😀"
    assert raw_text[SourceSpan(3, 4).start : SourceSpan(3, 4).end] == "B"


def test_source_span_tracks_zero_width_char_as_code_point() -> None:
    raw_text = "a\u200bb"

    assert len(raw_text) == 3
    assert raw_text[SourceSpan(1, 2).start : SourceSpan(1, 2).end] == "\u200b"


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (-1, 0),
        (2, 1),
        ("0", 1),
        (0, "1"),
    ],
)
def test_source_span_rejects_invalid_bounds(start: object, end: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        SourceSpan(start, end)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("char", "index"),
    [
        ("가", 0),
        ("😀", 1),
        ("\u200b", 2),
        ("㎡", 3),
    ],
)
def test_source_char_accepts_single_code_point_without_normalization(
    char: str, index: int
) -> None:
    source_char = SourceChar(char, index)

    assert source_char.char == char
    assert source_char.index == index


@pytest.mark.parametrize(
    ("char", "index"),
    [
        ("", 0),
        ("ab", 0),
        ("a", -1),
        (b"a", 0),
    ],
)
def test_source_char_rejects_invalid_values(char: object, index: int) -> None:
    with pytest.raises((TypeError, ValueError)):
        SourceChar(char, index)  # type: ignore[arg-type]
