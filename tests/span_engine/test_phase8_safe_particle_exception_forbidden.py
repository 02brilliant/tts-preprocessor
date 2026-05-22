from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI이 적용됐다", "에이아이이 적용됐다"),
        ("FTA이 적용됐다", "에프티에이이 적용됐다"),
        ("KOSPI이 올랐다", "코스피이 올랐다"),
        ("3이 맞다", "삼이 맞다"),
        ("5이 맞다", "오이 맞다"),
    ],
)
def test_a2_i_particle_is_noop(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI가 적용됐다", "에이아이가 적용됐다"),
        ("FTA가 적용됐다", "에프티에이가 적용됐다"),
        ("3가 맞다", "삼가 맞다"),
        ("3로 나누다", "삼로 나누다"),
        ("URL로 접속", "유알엘로 접속"),
        ("AI과 비교", "에이아이과 비교"),
        ("AI와 비교", "에이아이와 비교"),
        ("AI도 가능", "에이아이도 가능"),
    ],
)
def test_risky_particles_are_never_corrected(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("AI이", "에이아이가"),
        ("3이", "삼가"),
        ("AI가", "에이아이이"),
        ("3로", "삼으로"),
        ("AI과", "에이아이와"),
        ("AI와", "에이아이과"),
    ],
)
def test_forbidden_particle_signatures_do_not_appear(text: str, forbidden: str) -> None:
    assert transform(text) != forbidden
