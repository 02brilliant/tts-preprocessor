from __future__ import annotations

import pytest

from engine.main import transform


def prod(text: str) -> str:
    return transform(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("`3:4테스트`", "`3:4테스트`"),
        ('{"ratio":"3:4테스트"}', '{"ratio":"3:4테스트"}'),
        ("/path/3:4/log", "/path/3:4/log"),
        ("https://example.com?q=3:4테스트", "https://example.com?q=3:4테스트"),
        ("line 1:23", "line 1:23"),
        ("case 1:23", "case 1:23"),
        ("version 1:23", "version 1:23"),
        ("file 1:23", "file 1:23"),
        ("요한복음 3:16", "요한복음 3:16"),
    ],
)
def test_colon_protected_contexts_precede_broad_nm_claims(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("00:30", "영시 삼십분"),
        ("01:40", "한시 사십분"),
        ("09:30", "구시 삼십분"),
        ("3:04", "세시 사분"),
        ("13:05", "십삼시 오분"),
        ("24:09", "이십사시 구분"),
    ],
)
def test_strong_time_like_without_context_reads_as_time(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "3:40",
        "13:40",
        "24:50",
    ],
)
def test_ambiguous_time_like_without_context_currently_preserves(text: str) -> None:
    assert prod(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3:40에", "세시 사십분에"),
        ("24:50까지", "이십사시 오십분까지"),
    ],
)
def test_ambiguous_time_like_with_time_context_reads_as_time(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3:40 비율", "삼 대 사십 비율"),
        ("13:40 스코어", "십삼 대 사십 스코어"),
    ],
)
def test_ambiguous_time_like_ratio_score_context_reads_as_dae(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "회의 시간은 오후 3시 20분, 13:05, 10:30, 23:59이다.",
            "회의 시간은 오후 세 시 이십분, 십삼시 오분, 열시 삼십분, 이십삼시 오십구분이다.",
        ),
        (
            "회의 시간은 13:05, 10:30, 23:59이다.",
            "회의 시간은 십삼시 오분, 열시 삼십분, 이십삼시 오십구분이다.",
        ),
        (
            "회의는 13:05, 10:30, 23:59에 진행된다.",
            "회의는 십삼시 오분, 열시 삼십분, 이십삼시 오십구분에 진행된다.",
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
        ("비율은 16:9, 4:3이다", "비율은 십육 대 구, 사 대 삼이다"),
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
        ('{"times":"13:05, 10:30"}', '{"times":"13:05, 10:30"}'),
        ("/path/13:05,10:30/log", "/path/13:05,10:30/log"),
        ("https://example.com?q=13:05,10:30", "https://example.com?q=13:05,10:30"),
        ("[13:05, 10:30]", "13:05, 10:30"),
    ],
)
def test_comma_separated_time_like_list_protected_contexts_preserve(
    text: str, expected: str
) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("25:30", "이십오 대 삼십"),
        ("3:4", "삼 대 사"),
        ("13:5", "십삼 대 오"),
        ("1:234", "일 대 이백삼십사"),
        ("123:45", "백이십삼 대 사십오"),
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
