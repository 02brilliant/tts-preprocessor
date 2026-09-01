from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "USB3",
        "1e6",
        "3.2E-4",
        "1-1-9",
    ],
)
def test_ambiguous_or_unsupported_inputs_preserve(text: str) -> None:
    if text == "1-1-9":
        assert transform(text) == "일 일 구"
    else:
        assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[3kg]", "3kg"),
        ("(약) 3만원", "삼만 원"),
    ],
)
def test_phase9_bracket_filter_updates_former_phase7_preserve_cases(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("OpenAI", "Open에이아이"),
        ('유에스비삼', 'USB3'),
        ('A-1', '에이-일'),
        ('3~8cm', '삼~8cm'),
        ('50kg', '오십kg'),
        ('21명', '이십일명'),
        ('[3kg]', '[삼 킬로그램]'),
    ],
)
def test_forbidden_partial_outputs_do_not_appear(text: str, forbidden: str) -> None:
    assert transform(text) != forbidden
