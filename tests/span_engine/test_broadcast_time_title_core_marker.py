from __future__ import annotations

import pytest

from engine.main import transform as canonical_transform
from engine.span_engine import transform, transform_with_trace


def prod(text: str) -> str:
    return canonical_transform(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("KBS 24시뉴스이었습니다.", "케이비에스 이십사시뉴스이었습니다."),
        ("KBS 11시뉴스이었습니다.", "케이비에스 열한시뉴스이었습니다."),
        ("KBS 24시뉴스였습니다.", "케이비에스 이십사시뉴스였습니다."),
        ("KBS 11시뉴스입니다.", "케이비에스 열한시뉴스입니다."),
        ("24시뉴스", "이십사시뉴스"),
        ("24시뉴스룸", "이십사시뉴스룸"),
        ("24시뉴스특보", "이십사시뉴스특보"),
        ("24시뉴스데스크", "이십사시뉴스데스크"),
        ("24시뉴스이었습니다", "이십사시뉴스이었습니다"),
        (
            "지금까지 KBS 24시뉴스이었습니다. 시청해주셔서 감사합니다.",
            "지금까지 케이비에스 이십사시뉴스이었습니다. 시청해주셔서 감사합니다.",
        ),
    ],
)
def test_broadcast_time_title_core_marker_accepts_complete_hangul_tail(
    text: str, expected: str
) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("24시리즈", "이십사 시리즈"),
        ("24시스템", "이십사 시스템"),
    ],
)
def test_broadcast_time_lexical_si_words_use_residual_number_reading(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "24시점",
        "24시뉴스abc",
        "24시뉴스v2",
        "24시뉴스룸abc",
        "24시뉴스룸/log",
        "/path/24시뉴스이었습니다/log",
        "https://example.com?q=24시뉴스이었습니다",
        '{"title":"24시뉴스이었습니다"}',
        "`24시뉴스이었습니다`",
    ],
)
def test_broadcast_time_title_core_marker_preserves_unsafe_or_protected_text(
    text: str,
) -> None:
    assert transform(text) == text


def test_broadcast_time_title_core_marker_square_bracket_unwrap_preserves_inner() -> None:
    assert transform("[24시뉴스이었습니다]") == "24시뉴스이었습니다"


def test_broadcast_time_title_core_marker_provenance() -> None:
    output = transform_with_trace("24시뉴스이었습니다")

    assert output.normalized_text == "이십사시뉴스이었습니다"
    assert any(
        claim.owner == "time" and claim.reason == "time_hour_broadcast_title_suffix"
        for claim in output.trace.claim_logs
    )
    assert [(piece.text, piece.provenance) for piece in output.render_pieces] == [
        ("이십사", "GENERATED_READING"),
        ("시뉴스이었습니다", "ORIGINAL_KOREAN"),
    ]
