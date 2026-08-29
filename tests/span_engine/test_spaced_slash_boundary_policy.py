from __future__ import annotations

import pytest

from engine.span_engine import transform


def test_spaced_slash_boundary_transforms_each_numeric_unit_segment() -> None:
    text = "무게는 각각 -1.50kg / 12.5kg / 2.490 kg / +3.40kg / +3.210 kg 이다."
    expected = (
        "무게는 각각 마이너스 일쩜오영-킬로그램 / 십이쩜오-킬로그램 / "
        "이쩜사구영-킬로그램 / 플러스 삼쩜사영-킬로그램 / "
        "플러스 삼쩜이일영-킬로그램 이다."
    )
    assert transform(text) == expected


def test_spaced_slash_boundary_preserves_raw_delimiter_spacing() -> None:
    text = "무게는 각각 -1.50kg  /  12.5kg 이다."
    expected = "무게는 각각 마이너스 일쩜오영-킬로그램  /  십이쩜오-킬로그램 이다."
    assert transform(text) == expected


def test_spaced_slash_boundary_keeps_comma_list_parity() -> None:
    text = "무게는 각각 -1.50kg, 12.5kg, 2.490 kg, +3.40kg, +3.210 kg 이다."
    expected = (
        "무게는 각각 마이너스 일쩜오영-킬로그램, 십이쩜오-킬로그램, "
        "이쩜사구영-킬로그램, 플러스 삼쩜사영-킬로그램, "
        "플러스 삼쩜이일영-킬로그램 이다."
    )
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "무게는 각각 +.5kg / 12.5kg 이다.",
            "무게는 각각 +.5kg / 십이쩜오-킬로그램 이다.",
        ),
        (
            "무게는 각각 1,00kg / 12.5kg 이다.",
            "무게는 각각 1,00kg / 십이쩜오-킬로그램 이다.",
        ),
        (
            "무게는 각각 +01.5kg / 12.5kg 이다.",
            "무게는 각각 +01.5kg / 십이쩜오-킬로그램 이다.",
        ),
    ],
)
def test_spaced_slash_boundary_invalid_item_does_not_block_valid_item(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1/3", "삼분의 일"),
        ("2026/06/17", "이천이십육년 유월 십칠일"),
        ("15.2km/L", "리터당 십오쩜이 킬로미터"),
        ("90km/h", "시속 구십 킬로미터"),
        ("/path/1.5kg/log", "/path/1.5kg/log"),
        (
            "https://example.com?q=1.5kg/2kg",
            "https://example.com?q=1.5kg/2kg",
        ),
        ('{"value":"1.5kg / 2kg"}', '{"value":"1.5kg / 2kg"}'),
        ("`1.5kg / 2kg`", "`1.5kg / 2kg`"),
        ("[1.5kg / 2kg]", "1.5kg / 2kg"),
    ],
)
def test_spaced_slash_boundary_regression_surfaces_keep_existing_policy(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            '값은 {"value":"1.5kg / 2kg"} / 12.5kg 이다.',
            '값은 {"value":"1.5kg / 2kg"} / 십이쩜오-킬로그램 이다.',
        ),
        (
            "값은 `1.5kg / 2kg` / 12.5kg 이다.",
            "값은 `1.5kg / 2kg` / 십이쩜오-킬로그램 이다.",
        ),
        (
            "값은 [1.5kg / 2kg] / 12.5kg 이다.",
            "값은 1.5kg / 2kg / 십이쩜오-킬로그램 이다.",
        ),
    ],
)
def test_spaced_slash_boundary_does_not_split_inside_protected_spans(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_spaced_slash_boundary_does_not_create_no_hangul_slash_list() -> None:
    text = "-1.50kg / 12.5kg"
    assert transform(text) == "-1.50kg / 십이쩜오-킬로그램"


def test_spaced_slash_boundary_allows_fraction_owner_inside_segments() -> None:
    text = "값은 1/3 / 2/3 이다."
    expected = "값은 삼분의 일 / 삼분의 이 이다."
    assert transform(text) == expected
