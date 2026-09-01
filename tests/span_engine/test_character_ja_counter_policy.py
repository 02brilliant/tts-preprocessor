from __future__ import annotations

import pytest

from engine.span_engine.counter import (
    COUNTERS_BY_LENGTH,
    counter_number_reading,
    special_determiner_reading,
)
from engine.span_engine.transform import transform, transform_with_trace


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("제3자", "제-삼자"),
        ("제 3자", "제-삼자"),
        ("제12자", "제-십이자"),
        ("제 12자", "제-십이자"),
    ],
)
def test_je_prefixed_ja_uses_general_sino_reading_and_canonical_je_space(
    source: str, expected: str
) -> None:
    output = transform_with_trace(source)

    assert output.normalized_text == expected
    assert output.trace is not None
    assert any(
        log.owner == "numeric_suffix"
        and log.reason == "prefixed_ordinal_numeric_suffix"
        for log in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("3자녀", "세-자녀"),
        ("3자루", "세-자루"),
        ("3자리", "세-자리"),
        ("12자리", "열두-자리"),
        ("3자릿수", "세-자릿수"),
        ("3자매", "세-자매"),
        ("39자녀", "서른아홉-자녀"),
        ("40자녀", "사십-자녀"),
        ("39자릿수", "서른아홉-자릿수"),
        ("40자릿수", "사십-자릿수"),
    ],
)
def test_long_character_words_use_hybrid_counter_reading(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


def test_long_character_words_are_registered_longest_first() -> None:
    positions = {counter: COUNTERS_BY_LENGTH.index(counter) for counter in {
        "자녀",
        "자루",
        "자리",
        "자릿수",
        "자매",
    }}

    assert all(position < len(COUNTERS_BY_LENGTH) for position in positions.values())
    assert positions["자릿수"] < positions["자리"]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("이름1자", "이름 한-자"),
        ("이름 1자", "이름 한-자"),
        ("이름 2자", "이름 두-자"),
        ("이름 3자", "이름 석-자"),
        ("이름 4자", "이름 넉-자"),
        ("이름 13자", "이름 열세-자"),
        ("이름 14자", "이름 열네-자"),
    ],
)
def test_name_character_count_uses_special_three_and_four(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("비밀번호 4자", "비밀번호 네-자"),
        ("비밀번호는4자", "비밀번호는 네-자"),
        ("아이디3자", "아이디 세-자"),
        ("한글 3자 이내", "한글 세-자 이내"),
        ("영문 12자 이상", "영문 열두-자 이상"),
        ("문자 4자 입력", "문자 네-자 입력"),
        ("앞 3자", "앞 세-자"),
        ("뒤 4자", "뒤 네-자"),
        ("3자 입력", "세-자 입력"),
        ("4자 제한", "네-자 제한"),
    ],
)
def test_character_count_context_uses_hybrid_reading(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("길이 3자", "길이 석-자"),
        ("폭4자", "폭 넉-자"),
        ("쌀 4되", "쌀 넉-되"),
        ("쌀 3섬", "쌀 석-섬"),
        ("금 4돈", "금 너-돈"),
        ("쌀 3말", "쌀 서-말"),
        ("길이 4발", "길이 너-발"),
        ("금 3푼", "금 서-푼"),
        ("쌀을 3말", "쌀을 서-말"),
    ],
)
def test_clear_traditional_unit_context_uses_special_determiner(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("number", "counter", "expected"),
    [
        ("3", "냥", "석"),
        ("4", "냥", "넉"),
        ("3", "되", "석-"),
        ("4", "섬", "넉-"),
        ("3", "돈", "서-"),
        ("4", "말", "너-"),
        ("3", "발", "서-"),
        ("4", "푼", "너-"),
    ],
)
def test_special_determiner_counter_registry(
    number: str, counter: str, expected: str
) -> None:
    assert counter_number_reading(number, counter) == expected


def test_traditional_character_unit_shares_special_determiner_registry() -> None:
    assert special_determiner_reading(3, "자") == "석"
    assert special_determiner_reading(4, "자") == "넉"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("3자 회담", "삼자 회담"),
        ("4자 합의", "사자 합의"),
        ("5자 협의", "오자 협의"),
        ("4발", "사발"),
        ("4발표", "사발표"),
        ("3말했다", "삼말했다"),
    ],
)
def test_independent_ja_is_sino_and_ambiguous_units_do_not_use_special_forms(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("3냥", "석냥"),
        ("4냥", "넉냥"),
        ("금요일 3냥", "금요일 석냥"),
        ("금요일 4냥", "금요일 넉냥"),
        ("금 3냥", "금 석냥"),
        ("3 냥", "석 냥"),
    ],
)
def test_nyang_surface_is_sufficient_to_use_special_determiner(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "제3 자",
        "제 3 자",
        "03자",
        "이름 03자",
        "3자abc",
        "3자리abc",
        "제3자abc",
        "A3자",
        "`이름 3자`",
        '{"text":"한글 3자"}',
    ],
)
def test_character_ja_spacing_invalid_and_protected_boundaries(source: str) -> None:
    result = transform(source)

    if source == "제3 자":
        assert result == "제-삼자"
    elif source == "제 3 자":
        assert result == "제-삼자"
    elif source == "제3자abc":
        assert result == "제-삼자abc"
    else:
        assert result == source


def test_integer_only_special_determiner_policy_keeps_decimal_word_fallback() -> None:
    assert transform("7.25자료") == '칠-쩜-이오자료'
    assert transform("3.5말했다") == '삼-쩜-오말했다'
