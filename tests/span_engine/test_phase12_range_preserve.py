from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
        [
            "03~08",
            "1e3~2e3",
            "3~8cmabc",
            "3~8cm/s",
        "3~8AI",
        "~8",
        "3~",
        "3~~8",
    ],
)
def test_unsupported_ranges_preserve(text: str) -> None:
    assert transform(text) == text


def test_comma_integer_tilde_range_transforms_policy_update() -> None:
    assert transform("1,000~2,000") == "천에서 이천"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-3~8", "마이너스 삼에서 팔"),
        ("+3~8", "플러스 삼에서 팔"),
        ("3~8입니다", "삼에서 팔입니다"),
    ],
)
def test_broad_signed_tilde_ranges_transform(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3~8개", "삼에서 팔 개"),
        ("3~8명", "삼에서 팔 명"),
    ],
)
def test_range_compatible_korean_suffix_ranges_transform(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_decimal_right_endpoint_range_with_unit_policy_v1() -> None:
    assert transform("3~8.5kg") == "삼에서 팔쩜오 킬로그램"


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("3.5~8kg", "삼점오에서 팔 킬로그램"),
        ("3~8cmabc", "삼에서 팔 센티미터abc"),
        ("2025-01-03", "이천이십오-일-삼"),
    ],
)
def test_unsupported_range_forbidden_signatures_do_not_appear(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden
