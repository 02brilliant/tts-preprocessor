from __future__ import annotations

import pytest

from engine.span_engine import transform


NEW_HYBRID_COUNTERS = [
    "석",
    "표",
    "매",
    "문항",
    "문제",
    "곡",
    "장면",
    "세트",
    "팩",
    "봉",
    "종류",
    "항목",
    "사례",
]


@pytest.mark.parametrize("counter", NEW_HYBRID_COUNTERS)
@pytest.mark.parametrize(
    ("number", "reading"),
    [
        ('2', '두'),
        ('39', '서른아홉'),
        ("40", "사십"),
        ("99", "구십구"),
        ("100", "백"),
        ("101", "백일"),
    ],
)
def test_additional_hybrid_counters(
    counter: str, number: str, reading: str
) -> None:
    assert transform(f"{number}{counter}") == f"{reading}-{counter}"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2대", "2대"),
        ("39대", "39대"),
        ("40대", "사십-대"),
        ("101대", "백일-대"),
        ("2항목", "두-항목"),
        ("39항목", "서른아홉-항목"),
        ("40항목", "사십-항목"),
        ("101항목", "백일-항목"),
        ("2사례", "두-사례"),
        ("40사례", "사십-사례"),
        ("101사례", "백일-사례"),
        ("2종류", "두-종류"),
        ("40종류", "사십-종류"),
        ("101종류", "백일-종류"),
        ("1척", "1척"),
        ("2척", "2척"),
        ("3척", "3척"),
        ("4척", "4척"),
        ("10척", "10척"),
        ("20척", "20척"),
        ("21척", "21척"),
        ("29척", "29척"),
        ("31척", "31척"),
        ("39척", "39척"),
        ("40척", "사십-척"),
        ("99척", "구십구-척"),
        ("100척", "백-척"),
        ("101척", "백일-척"),
        ("139척", "백삼십구-척"),
        ("140척", "백사십-척"),
        ("1척을", "1척을"),
        ("2척은", "2척은"),
        ("29척이", "29척이"),
        ("39척까지", "39척까지"),
        ("40척부터", "사십-척부터"),
        ("100척을", "백-척을"),
        (
            "배가 1척 있습니다. 앞으로 29척, 39척, 40척 만들 예정입니다.",
            "배가 한-척 있습니다. 앞으로 29척, 39척, 사십-척 만들 예정입니다.",
        ),
    ],
)
def test_additional_hybrid_counter_examples(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2대abc", "2대abc"),
        ("2장면abc", "2장면abc"),
        ("2봉지abc", "2봉지abc"),
        ("2항목abc", "2항목abc"),
        ("2사례test", "2사례test"),
        ("2종류A", "2종류A"),
        ("1척abc", "1척abc"),
        ("2척A", "2척A"),
        ("29척v2", "29척v2"),
        ("A1척", "A1척"),
        ("model-1척", "model-1척"),
        ("A2항목", "A2항목"),
        ("model-2대", "model-2대"),
    ],
)
def test_additional_hybrid_counter_unsafe_preserve(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("제2항목", "제-이항목"),
        ("제2사례", "제-이사례"),
        ("제2대", "제-이대"),
        ("제2문항", "제-이문항"),
    ],
)
def test_additional_hybrid_counters_do_not_expand_ordinal_targets(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2쪽", "이쪽"),
        ("40쪽", "사십쪽"),
        ("2부", "2부"),
        ("40부", "사십-부"),
    ],
)
def test_excluded_counters_keep_existing_behavior(
    source: str, expected: str
) -> None:
    assert transform(source) == expected
