from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1시", "한시"),
        ("2시", "두~시"),
        ("3시", "세~시"),
        ("4시", "네~시"),
        ("10시", "열~시"),
        ("11시", "열~한시"),
        ("12시", "열~두시"),
        ("13시", "십삼시"),
        ("19시", "십구시"),
        ("20시", "이~십시"),
        ("21시", "이~십일시"),
        ("22시", "이~십이시"),
        ("23시", "이~십삼시"),
        ("24시", "이~십사시"),
        ("0시", "영시"),
        ("00시", "영시"),
    ],
)
def test_clock_hour_suffix_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0시부로", "영시부로"),
        ("1시부로", "한시부로"),
        ("9시께", "아홉시께"),
        ("1시반", "한시반"),
        ("12시반", "열~두시반"),
        ("3시방향", "세-시 방향"),
        ("1시부터는", "한시부터는"),
        ("2시까지로", "두~시까지로"),
        ("1시입니다만", "한시입니다만"),
        ("3시방향으로", "세-시 방향으로"),
        ("1시반도", "한시반도"),
        ("13시부로", "십삼시부로"),
    ],
)
def test_clock_hour_meaning_tails_and_particle_chain(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시리즈", "삼-시리즈"),
        ("6분께", "6분께"),
        ("6분께서", "6분께서"),
        ("3초반", "3초반"),
        ("3시회의", "3시회의"),
    ],
)
def test_clock_hour_meaning_tails_do_not_expand_unrelated_surfaces(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("오전 9시 5분", "오전 아홉시 오~분"),
        ("오후 3시 20분", "오후 세~시 이~십분"),
        ("23시 59분", "이~십삼시 오~십구분"),
    ],
)
def test_clock_hour_with_minute_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1시간", "한-시간"),
        ("2시간", "두~시간"),
        ("3시간", "세~시간"),
        ("4시간", "네~시간"),
        ("10시간", "열~시간"),
        ("11시간", "열~한-시간"),
        ("12시간", "열~두-시간"),
        ("13시간", "열~세-시간"),
        ("19시간", "열~아홉-시간"),
        ("20시간", "스무-시간"),
        ("21시간", "스물한-시간"),
        ("22시간", "스물두-시간"),
        ("23시간", "스물세-시간"),
        ("24시간", "이~십사-시간"),
        ("48시간", "사~십팔-시간"),
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
        ("7시간 05분", "일곱-시간 오~분"),
        ("2시간 32분", "두~시간 삼십이분"),
        ("20시간 10분", "스무-시간 십분"),
        ("24시간 30분", "이~십사-시간 삼십분"),
    ],
)
def test_duration_hour_with_minute_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2~3시 회의", "두~시에서 세~시 회의"),
        ("10~12시 회의", "열~시에서 열~두시 회의"),
        ("13~15시 회의", "십삼시에서 십오시 회의"),
        ("20~22시 회의", "이~십시에서 이~십이시 회의"),
        ("7~9시간 작업", "일곱-시간에서 아홉-시간 작업"),
        ("20~22시간 작업", "스무-시간에서 스물두-시간 작업"),
        ("24~48시간 작업", "이~십사-시간에서 사~십팔-시간 작업"),
    ],
)
def test_clock_and_duration_shared_suffix_ranges(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1~5일 조사", "일일에서 오~일 조사"),
        ("10~20분 대기", "십분에서 이~십분 대기"),
        ("5~7쪽", "오~에서 칠쪽"),
        ("12-15장", "십이에서 십오-장"),
        ("3:2", "삼 대 이~"),
        ("1-1 무", "1-1 무"),
    ],
)
def test_out_of_scope_ranges_and_scores_remain_unchanged(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
