from __future__ import annotations

import pytest

from engine.main import transform


def prod(text: str) -> str:
    return transform(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("`3:4테스트`", "`3:4테스트`"),
        ('{"ratio":"3:4테스트"}', '"ratio":"3:4테스트"'),
        ("/path/3:4/log", "/path/3:4/log"),
        ("https://example.com?q=3:4테스트", "https://example.com?q=3:4테스트"),
        ("line 1:23", "line 1:23"),
        ("case 1:23", "case 1:23"),
        ("version 1:23", "version 1:23"),
        ("file 1:23", "file 1:23"),
        ("요한복음 3:16", "요한복음 3:16"),
        ("점수는 09:30이다", "점수는 09:30이다"),
        ("비율은 09:30이다", "비율은 09:30이다"),
        ("요한복음 09:30", "요한복음 09:30"),
        ("line 09:30", "line 09:30"),
        ("case 09:30", "case 09:30"),
        ("file 09:30", "file 09:30"),
        ("/path/09:30/log", "/path/09:30/log"),
        ("https://example.com?t=09:30", "https://example.com?t=09:30"),
        ('{"time":"09:30"}', '"time":"09:30"'),
        ("`09:30`", "`09:30`"),
    ],
)
def test_colon_protected_contexts_precede_broad_nm_claims(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0:00", "영시"),
        ("0:05", "영시 오~분"),
        ("00:00", "영시"),
        ("00:30", "영시 삼십분"),
        ("01:00", "한시"),
        ("01:40", "한시 사~십분"),
        ("02:30", "두~시 삼십분"),
        ("03:30", "세~시 삼십분"),
        ("04:30", "네~시 삼십분"),
        ("05:30", "다섯시 삼십분"),
        ("06:30", "여섯시 삼십분"),
        ("07:30", "일곱시 삼십분"),
        ("08:30", "여덟시 삼십분"),
        ("09:00", "아홉시"),
        ("09:30", "아홉시 삼십분"),
        ("09:59", "아홉시 오~십구분"),
        ("10:00", "열~시"),
        ("11:05", "열~한시 오~분"),
        ("12:00", "열~두시"),
        ("3:04", "세~시 사~분"),
        ("13:00", "십삼시"),
        ("13:05", "십삼시 오~분"),
        ("20:00", "이~십시"),
        ("24:00", "이~십사시"),
        ("24:09", "이~십사시 구분"),
    ],
)
def test_strong_time_like_without_context_reads_as_time(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "3:40",
        "0:30",
        "10:30",
        "11:30",
        "12:59",
        "13:40",
        "19:30",
        "21:30",
        "22:30",
        "23:59",
        "24:50",
    ],
)
def test_ambiguous_time_like_without_context_currently_preserves(text: str) -> None:
    assert prod(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3:40에", "세~시 사~십분에"),
        ("10:30에", "열~시 삼십분에"),
        ("11:30에", "열~한시 삼십분에"),
        ("12:59에", "열~두시 오~십구분에"),
        ("19:30에", "십구시 삼십분에"),
        ("21:30에", "이~십일시 삼십분에"),
        ("22:30에", "이~십이시 삼십분에"),
        ("23:59에", "이~십삼시 오~십구분에"),
        ("24:50까지", "이~십사시 오~십분까지"),
    ],
)
def test_ambiguous_time_like_with_time_context_reads_as_time(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("09시", "아홉시"),
        ("09시다", "아홉시다"),
        ("07시 05분", "일곱시 오~분"),
        ("0시", "영시"),
        ("00시", "영시"),
        ("09 시", "09 시"),
    ],
)
def test_leading_zero_suffix_clock_uses_suffix_time_policy(
    text: str, expected: str
) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3:40 비율", "삼 대 사~십 비율"),
        ("13:40 스코어", "십삼 대 사~십 스코어"),
    ],
)
def test_ambiguous_time_like_ratio_score_context_reads_as_dae(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "회의 시간은 오후 3시 20분, 13:05, 10:30, 23:59이다.",
            "회의 시간은 오후 세~시 이~십분, 십삼시 오~분, 열~시 삼십분, 이~십삼시 오~십구분이다.",
        ),
        (
            "회의 시간은 13:05, 10:30, 23:59이다.",
            "회의 시간은 십삼시 오~분, 열~시 삼십분, 이~십삼시 오~십구분이다.",
        ),
        (
            "회의는 13:05, 10:30, 23:59에 진행된다.",
            "회의는 십삼시 오~분, 열~시 삼십분, 이~십삼시 오~십구분에 진행된다.",
        ),
        (
            "일정은 09:30, 14:00, 18:30입니다.",
            "일정은 아홉시 삼십분, 십사시, 십팔시 삼십분입니다.",
        ),
    ],
)
def test_comma_separated_time_list_with_explicit_context_reads_as_time(
    text: str, expected: str
) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("13:40, 24:50", "13:40, 24:50"),
        ("메모는 10:30, 23:59", "메모는 10:30, 23:59"),
        ("비율은 16:9, 4:3이다", "비율은 십육 대 구, 사~ 대 삼이다"),
        ("요한복음 3:16, 4:12", "요한복음 3:16, 4:12"),
        ("line 10:20, 30:40", "line 10:20, 30:40"),
        ("version 1:23, 2:34", "version 1:23, 2:34"),
    ],
)
def test_comma_separated_time_like_list_preserve_and_context_regressions(
    text: str, expected: str
) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("`13:05, 10:30`", "`13:05, 10:30`"),
        ('{"times":"13:05, 10:30"}', '"times":"13:05, 10:30"'),
        ("/path/13:05,10:30/log", "/path/13:05,10:30/log"),
        ("https://example.com?q=13:05,10:30", "https://example.com?q=13:05,10:30"),
        ("[13:05, 10:30]", '[13:05, 10:30]'),
    ],
)
def test_comma_separated_time_like_list_protected_contexts_preserve(
    text: str, expected: str
) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("25:30", "이~십오 대 삼십"),
        ("3:4", "삼 대 사~"),
        ("13:5", "십삼 대 오~"),
        ("1:234", "일 대 이~백삼십사"),
        ("123:45", "백이십삼 대 사~십오"),
    ],
)
def test_non_time_like_nm_fallback_current_policy(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "+01:2",
        "+1.:2",
        "+.5:2",
        "1,00:2",
        "01:2:3",
        "1:+2.:3",
        "1,00:2:3",
    ],
)
def test_invalid_colon_surfaces_preserve_without_partial_fallback(text: str) -> None:
    assert prod(text) == text
