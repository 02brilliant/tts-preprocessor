from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "3.5명abc",
        "-.5℃",
        "값은 -.5℃다",
        "-.5℉",
        "값은 -.5℉다",
        "-.5℃abc",
    ],
)
def test_decimal_fallback_does_not_invade_invalid_owner_candidates_policy_v1(
    text: str,
) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.5명", "삼쩜오 명"),
        ("3.5명은", "삼쩜오 명은"),
        ("3.5명입니다", "삼쩜오 명입니다"),
        ("참가자는 3.5명이다", "참가자는 삼쩜오 명이다"),
        ("3.5개", "삼쩜오 개"),
    ],
)
def test_decimal_registered_counter_suffixes_now_transform_policy_v1(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("21명", "스물한 명"),
        ("12권", "열두 권"),
        ("-2.5℃", "영하 이쩜오도"),
        ("-2.5℉", "화씨 영하 이쩜오도"),
        ("3.14", "삼쩜일사"),
        ("12.3수치", "십이쩜삼수치"),
        ("7.25자료", "칠쩜이오자료"),
    ],
)
def test_supported_decimal_counter_and_signed_paths_remain_policy_v1(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
