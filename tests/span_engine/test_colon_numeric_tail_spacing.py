from __future__ import annotations

from engine.span_engine.transform import transform


def test_colon_numeric_broad_reading_basics() -> None:
    cases = [
        ("3:4", "삼 대 사"),
        ("+1:2", "플러스 일 대 이"),
        ("13:5", "십삼 대 오"),
        ("1.5:2.0", "일쩜오 대 이쩜영"),
        ("1.50:2", "일쩜오영 대 이"),
        ("1,000:2,000", "천 대 이천"),
        ("+1,000.50:2", "플러스 천쩜오영 대 이"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_numeric_adjacent_korean_tail_spacing() -> None:
    cases = [
        ("3:4테스트", "삼 대 사 테스트"),
        ("+1:2테스트", "플러스 일 대 이 테스트"),
        ("-1:+2범위", "마이너스 일 대 플러스 이 범위"),
        ("1.5:2.0범위", "일쩜오 대 이쩜영 범위"),
        ("1.50:2테스트", "일쩜오영 대 이 테스트"),
        ("1,000:2,000테스트", "천 대 이천 테스트"),
        ("+1,000.50:2범위", "플러스 천쩜오영 대 이 범위"),
        ("13:5테스트", "십삼 대 오 테스트"),
        ("3:4구간", "삼 대 사 구간"),
        ("3:4숫자범위", "삼 대 사 숫자범위"),
        ("3:4값", "삼 대 사 값"),
        ("3:4입력값", "삼 대 사 입력값"),
        ("3:4케이스", "삼 대 사 케이스"),
        ("3:4결과", "삼 대 사 결과"),
        ("3:4스코어", "삼 대 사 스코어"),
        ("3:4비율", "삼 대 사 비율"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_numeric_spaced_korean_tail_regression() -> None:
    cases = [
        ("3:4 테스트", "삼 대 사 테스트"),
        ("+1:2 테스트", "플러스 일 대 이 테스트"),
        ("-1:+2 범위", "마이너스 일 대 플러스 이 범위"),
        ("1.5:2.0 범위", "일쩜오 대 이쩜영 범위"),
        ("1,000:2,000 테스트", "천 대 이천 테스트"),
        ("13:5 테스트", "십삼 대 오 테스트"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_numeric_fullwidth_colon_tail_spacing() -> None:
    cases = [
        ("3：4테스트", "삼 대 사 테스트"),
        ("+1：2테스트", "플러스 일 대 이 테스트"),
        ("1.5：2.0범위", "일쩜오 대 이쩜영 범위"),
        ("1,000：2,000테스트", "천 대 이천 테스트"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_numeric_sentence_punctuation() -> None:
    cases = [
        ("3:4.", "삼 대 사."),
        ("+1:2.", "플러스 일 대 이."),
        ("1.5:2.0.", "일쩜오 대 이쩜영."),
        ("1,000:2,000.", "천 대 이천."),
        ("3:4테스트.", "삼 대 사 테스트."),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_numeric_time_like_preserve_or_time_policy() -> None:
    cases = [
        ("09:30테스트", "09:30테스트"),
        ("09:30 테스트", "구시 삼십분 테스트"),
        ("24:09테스트", "24:09테스트"),
        ("24:09 테스트", "이십사시 구분 테스트"),
        ("3:04테스트", "3:04테스트"),
        ("+1:02테스트", "+1:02테스트"),
        ("13:05에 시작", "십삼시 오분에 시작"),
        ("24:09까지", "이십사시 구분까지"),
    ]
    for source, expected in cases:
        assert transform(source) == expected
        assert " 대 " not in transform(source)


def test_colon_numeric_protected_and_code_like_preserve() -> None:
    for source in (
        "line 3:4테스트",
        "case 3:4테스트",
        "version 1:2테스트",
        "/path/3:4테스트/log",
        "/path/+1:2/log",
        "`3:4테스트`",
        "`+1:2`",
        '{"ratio":"3:4테스트"}',
    ):
        assert transform(source) == source


def test_colon_numeric_invalid_preserve_and_blocks_partial_fallback() -> None:
    for source in (
        "03:4테스트",
        "3:04테스트",
        "+01:2테스트",
        "+1.:2테스트",
        "+.5:2테스트",
        "1,00:2테스트",
    ):
        assert transform(source) == source


def test_colon_numeric_multi_colon_regression() -> None:
    cases = [
        ("1:2:3", "일 대 이 대 삼"),
        ("+1:2:-3:4", "플러스 일 대 이 대 마이너스 삼 대 사"),
        ("1:2:3:4:5:6:7:8", "일 대 이 대 삼 대 사 대 오 대 육 대 칠 대 팔"),
        ("1:2:3:4:5:6:7:8:9", "1:2:3:4:5:6:7:8:9"),
        ("1:02:03", "1:02:03"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_numeric_long_integrated_sentences() -> None:
    source = (
        "3:4테스트, 3:4 테스트, 3:4. +1:2테스트, +1:2 테스트, +1:2. "
        "1.5:2.0범위, 1.5:2.0 범위, 1.5:2.0. "
        "1,000:2,000테스트, 1,000:2,000 테스트, 1,000:2,000."
    )
    expected = (
        "삼 대 사 테스트, 삼 대 사 테스트, 삼 대 사. "
        "플러스 일 대 이 테스트, 플러스 일 대 이 테스트, 플러스 일 대 이. "
        "일쩜오 대 이쩜영 범위, 일쩜오 대 이쩜영 범위, 일쩜오 대 이쩜영. "
        "천 대 이천 테스트, 천 대 이천 테스트, 천 대 이천."
    )
    assert transform(source) == expected

    source = (
        "09:30까지, 09:30 테스트, 24:09까지, 24:09 테스트, "
        "25:30까지, 25:30 테스트, 13:5테스트, 13:5 테스트."
    )
    expected = (
        "09:30까지, 09:30 테스트, 24:09까지, 24:09 테스트, "
        "25:30까지, 이십오 대 삼십 테스트, 십삼 대 오 테스트, 십삼 대 오 테스트."
    )
    assert transform(source) == expected
