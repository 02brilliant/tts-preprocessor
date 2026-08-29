from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시간", "세-시간"),
        ("7시간", "일곱-시간"),
        ("0시간", "영-시간"),
        ("1,200시간", "천이백-시간"),
        ("2.5시간", "이쩜오-시간"),
        ("1/2시간", "이분의 일-시간"),
        ("-3시간", "마이너스 세-시간"),
        ("-2.5시간", "마이너스 이쩜오-시간"),
        ("-1/2시간", "마이너스 이분의 일-시간"),
    ],
)
def test_phase34b_duration_hour_only(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("18분", "18분"),
        ("05분", "05분"),
        ("0분", "영-분"),
        ("1,200분", "천이백-분"),
        ("2.5분", "이쩜오-분"),
        ("1/2분", "이분의 일 분"),
        ("-18분", "마이너스 십팔 분"),
        ("-2.5분", "마이너스 이쩜오 분"),
        ("-1/2분", "마이너스 이분의 일 분"),
    ],
)
def test_phase34b_duration_minute_only(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시간 18분", "세-시간 십팔분"),
        ("7시간 05분", "일곱-시간 오분"),
        ("1,200시간 30분", "천이백-시간 삼십분"),
        ("2.5시간 30분", "이쩜오-시간 삼십분"),
        ("1/2시간 30분", "이분의 일-시간 삼십분"),
        ("3시간 1/2분", "세-시간 이분의 일분"),
        ("-3시간 18분", "마이너스 세-시간 십팔분"),
        ("3시간 -18분", "세-시간 마이너스 십팔분"),
    ],
)
def test_phase34b_duration_hour_minute_with_space(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시간18분", "세-시간 십팔분"),
        ("7시간05분", "일곱-시간 오분"),
        ("1,200시간30분", "천이백-시간 삼십분"),
        ("2.5시간30분", "이쩜오-시간 삼십분"),
        ("1/2시간30분", "이분의 일-시간 삼십분"),
        ("-3시간18분", "마이너스 세-시간 십팔분"),
        ("3시간-18분", "세-시간-18분"),
    ],
)
def test_phase34b_duration_hour_minute_without_space(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2.5%p", "이쩜오-퍼센트포인트"),
        ("-2.5%p", "마이너스 이쩜오-퍼센트포인트"),
        ("1/2%p", "이분의 일-퍼센트포인트"),
        ("1,200%p", "천이백-퍼센트포인트"),
        ("0.5%p", "영쩜오-퍼센트포인트"),
        ("33%p", "삼십삼-퍼센트포인트"),
        ("2.5%point", "2.5%point"),
        ("2.5%pa", "2.5%pa"),
        ("A2.5%p", "A2.5%p"),
    ],
)
def test_phase34b_percent_point(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1/3", "삼분의 일"),
        ("4/7", "칠분의 사"),
        ("10/25", "이십오분의 십"),
        ("-1/3", "마이너스 삼분의 일"),
        ("-4/7", "마이너스 칠분의 사"),
        ("1,200/3,400", "삼천사백분의 천이백"),
        (
            "123,456/123,456,789",
            "일억이천삼백사십오만육천칠백팔십구분의 십이만삼천사백오십육",
        ),
        ("1 / 3", "1 / 3"),
        ("1/ 3", "1/ 3"),
        ("1 /3", "1 /3"),
        ("1.5/3", "1.5/3"),
        ("1/3.5", "1/3.5"),
        ("1/3abc", "1/3abc"),
        ("abc1/3", "abc1/3"),
        ("A/B", "A/B"),
        ("USB/300", "USB/300"),
        ("0/3", "0/3"),
        ("1/0", "1/0"),
        ("12,34/56", "12,34/56"),
    ],
)
def test_phase34b_slash_fraction(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("15.2km/L", "리터당 십오쩜이 킬로미터"),
        ("3km/s", "초속 삼 킬로미터"),
        ("km/L", "km/L"),
        ("2026-04-17", "이천이십육년 사월 십칠일"),
        ("3:2 승", "삼 대 이 승"),
        ("2:1", "이 대 일"),
        ("2.5%", "이쩜오-퍼센트"),
        ("2.5%p", "이쩜오-퍼센트포인트"),
    ],
)
def test_phase34b_conflict_regression(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "경기 시간은 3시간 18분이고 금리 차는 2.5%p이며 비율은 1/3이다.",
            "경기 시간은 세-시간 십팔분이고 금리 차는 이쩜오-퍼센트포인트이며 비율은 삼분의 일이다.",
        ),
        (
            "향후 2주 동안 발표될 지표와 1/3 확률, -1/3 조정폭, 2.5%p 변동을 함께 본다.",
            "향후 이주 동안 발표될 지표와 삼분의 일 확률, 마이너스 삼분의 일 조정폭, 이쩜오-퍼센트포인트 변동을 함께 본다.",
        ),
    ],
)
def test_phase34b_compound_sentences(text: str, expected: str) -> None:
    assert transform(text) == expected
