from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1시", "한 시"),
        ("2시", "두 시"),
        ("3시", "세 시"),
        ("4시", "네 시"),
        ("10시", "열 시"),
        ("11시", "열한 시"),
        ("12시", "열두 시"),
        ("13시", "십삼 시"),
        ("19시", "십구 시"),
        ("20시", "이십 시"),
        ("21시", "이십일 시"),
        ("22시", "이십이 시"),
        ("23시", "이십삼 시"),
        ("24시", "이십사 시"),
        ("0시", "영 시"),
        ("00시", "영 시"),
    ],
)
def test_clock_hour_suffix_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("오전 9시 5분", "오전 아홉 시 오분"),
        ("오후 3시 20분", "오후 세 시 이십분"),
        ("23시 59분", "이십삼 시 오십구분"),
    ],
)
def test_clock_hour_with_minute_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1시간", "한 시간"),
        ("2시간", "두 시간"),
        ("3시간", "세 시간"),
        ("4시간", "네 시간"),
        ("10시간", "열 시간"),
        ("11시간", "열한 시간"),
        ("12시간", "열두 시간"),
        ("13시간", "열세 시간"),
        ("19시간", "열아홉 시간"),
        ("20시간", "스무 시간"),
        ("21시간", "스물한 시간"),
        ("22시간", "스물두 시간"),
        ("23시간", "스물세 시간"),
        ("24시간", "이십사 시간"),
        ("48시간", "사십팔 시간"),
    ],
)
def test_duration_hour_suffix_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 시", "일 시"),
        ("3 시", "삼 시"),
        ("09 시", "09 시"),
        ("13 시", "십삼 시"),
        ("1 시간", "일 시간"),
        ("3 시간", "삼 시간"),
        ("09 시간", "09 시간"),
        ("13 시간", "십삼 시간"),
    ],
)
def test_spaced_clock_and_duration_markers_use_ordinary_number_reading(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("7시간 05분", "일곱 시간 오분"),
        ("2시간 32분", "두 시간 삼십이분"),
        ("20시간 10분", "스무 시간 십분"),
        ("24시간 30분", "이십사 시간 삼십분"),
    ],
)
def test_duration_hour_with_minute_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2~3시 회의", "두 시에서 세 시 회의"),
        ("10~12시 회의", "열 시에서 열두 시 회의"),
        ("13~15시 회의", "십삼 시에서 십오 시 회의"),
        ("20~22시 회의", "이십 시에서 이십이 시 회의"),
        ("7~9시간 작업", "일곱 시간에서 아홉 시간 작업"),
        ("20~22시간 작업", "스무 시간에서 스물두 시간 작업"),
        ("24~48시간 작업", "이십사 시간에서 사십팔 시간 작업"),
    ],
)
def test_clock_and_duration_shared_suffix_ranges(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1~5일 조사", "일일에서 오일 조사"),
        ("10~20분 대기", "십분에서 이십분 대기"),
        ("5~7쪽", "오에서 칠쪽"),
        ("12-15장", "십이에서 십오 장"),
        ("3:2", "삼 대 이"),
        ("1-1 무", "1-1 무"),
    ],
)
def test_out_of_scope_ranges_and_scores_remain_unchanged(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
