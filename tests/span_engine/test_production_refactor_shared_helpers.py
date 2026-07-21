from __future__ import annotations

import pytest

from engine.span_engine import prosody, prosody_extra
from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import RenderPiece, SourceSpan
from engine.span_engine.span_guards import span_overlaps_excluded_ranges


def _square_range(start: int, end: int) -> BracketRange:
    return BracketRange(
        bracket_type="square",
        span=SourceSpan(start, end),
        inner_span=SourceSpan(start + 1, end - 1),
        raw="[" + "x" * max(0, end - start - 2) + "]",
    )


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        pytest.param(SourceSpan(0, 2), False, id="touches-left-edge"),
        pytest.param(SourceSpan(1, 3), True, id="crosses-left-edge"),
        pytest.param(SourceSpan(2, 6), True, id="same-range"),
        pytest.param(SourceSpan(5, 7), True, id="crosses-right-edge"),
        pytest.param(SourceSpan(6, 8), False, id="touches-right-edge"),
    ],
)
def test_shared_excluded_range_overlap_uses_half_open_spans(
    span: SourceSpan, expected: bool
) -> None:
    excluded = [_square_range(2, 6)]

    assert span_overlaps_excluded_ranges(span, excluded) is expected


def test_shared_excluded_range_overlap_accepts_empty_exclusions() -> None:
    assert span_overlaps_excluded_ranges(SourceSpan(0, 3), []) is False


@pytest.mark.parametrize("module", [prosody, prosody_extra])
def test_prosody_range_merge_contract(module: object) -> None:
    merge_ranges = getattr(module, "_merge_ranges")

    assert merge_ranges([]) == []
    assert merge_ranges([(5, 5), (4, 8), (0, 2), (2, 4), (10, 9)]) == [
        (0, 8)
    ]


@pytest.mark.parametrize("module", [prosody, prosody_extra])
def test_prosody_visible_position_contract(module: object) -> None:
    previous_visible_index = getattr(module, "_previous_visible_index")
    previous_whitespace_run_start = getattr(
        module, "_previous_whitespace_run_start"
    )
    next_non_space_index = getattr(module, "_next_non_space_index")

    assert previous_visible_index("가   나", 4) == 0
    assert previous_visible_index("   가", 3) is None
    assert previous_whitespace_run_start("가   나", 4) == 1
    assert previous_whitespace_run_start("가나", 1) == 1
    assert next_non_space_index("가   나", 1) == 4
    assert next_non_space_index("가   ", 1) is None


@pytest.mark.parametrize("module", [prosody, prosody_extra])
def test_prosody_render_piece_insertion_lookup_uses_half_open_spans(
    module: object,
) -> None:
    find_piece_index = getattr(module, "_find_piece_index_for_insertion")
    pieces = [
        RenderPiece(
            text="가",
            provenance="ORIGINAL_KOREAN",
            source_span=SourceSpan(0, 1),
        ),
        RenderPiece(text=",", provenance="GENERATED_PUNCT", source_span=None),
        RenderPiece(
            text="나다",
            provenance="ORIGINAL_KOREAN",
            source_span=SourceSpan(2, 4),
        ),
    ]

    assert find_piece_index(pieces, 0) == 0
    assert find_piece_index(pieces, 1) is None
    assert find_piece_index(pieces, 2) == 2
    assert find_piece_index(pieces, 4) is None

