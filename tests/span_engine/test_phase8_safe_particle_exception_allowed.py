from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("FTA은 적용됐다", "에프티에이는 적용됐다"),
        ("FTA는 적용됐다", "에프티에이는 적용됐다"),
        ("AI은 중요하다", "에이아이는 중요하다"),
        ("AI는 중요하다", "에이아이는 중요하다"),
        ("KOSPI은 올랐다", "코스피는 올랐다"),
        ("KOSPI는 올랐다", "코스피는 올랐다"),
        ("ABC는 테스트다", "에이비씨는 테스트다"),
        ("URL는 접속했다", "유알엘은 접속했다"),
        ("URL은 접속했다", "유알엘은 접속했다"),
    ],
)
def test_safe_particle_exception_allows_eun_neun(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("FTA을 적용했다", "에프티에이를 적용했다"),
        ("FTA를 적용했다", "에프티에이를 적용했다"),
        ("AI을 적용했다", "에이아이를 적용했다"),
        ("AI를 적용했다", "에이아이를 적용했다"),
        ("URL를 열었다", "유알엘을 열었다"),
        ("URL을 열었다", "유알엘을 열었다"),
        ("3를 더했다", "삼을 더했다"),
        ("3을 더했다", "삼을 더했다"),
        ("5을 더했다", "오를 더했다"),
        ("5를 더했다", "오를 더했다"),
        ("10는 많다", "십은 많다"),
        ("10은 많다", "십은 많다"),
    ],
)
def test_safe_particle_exception_allows_eul_reul(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI으로 처리", "에이아이로 처리"),
        ("FTA으로 처리", "에프티에이로 처리"),
        ("3으로 나누다", "삼으로 나누다"),
        ("5으로 나누다", "오로 나누다"),
        ("URL으로 접속", "유알엘로 접속"),
        ("10으로 이동", "십으로 이동"),
        ("AI로 처리", "에이아이로 처리"),
        ("3로 나누다", "삼로 나누다"),
        ("URL로 접속", "유알엘로 접속"),
    ],
)
def test_safe_particle_exception_allows_only_euro_not_ro(text: str, expected: str) -> None:
    assert transform(text) == expected
