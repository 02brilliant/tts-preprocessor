from __future__ import annotations

import pytest

from engine.main import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시리즈", "삼 시리즈"),
        ("12시리즈", "십이 시리즈"),
        ("+3시리즈", "플러스 삼 시리즈"),
        ("-3시리즈", "마이너스 삼 시리즈"),
        ("제3시리즈", "제 삼시리즈"),
        ("제 3시리즈", "제 삼시리즈"),
        ("1분기", "일분기"),
        ("+1분기", "플러스 일분기"),
        ("-1분기", "마이너스 일분기"),
        ("제1분기", "제 일분기"),
        ("1.5분기", "일쩜오 분기"),
        ("+1.5분기", "플러스 일쩜오 분기"),
    ],
)
def test_series_and_quarter_signed_and_prefixed_readings(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("39조각", "서른아홉 조각"),
        ("40조각", "사십 조각"),
        ("+3조각", "플러스 세 조각"),
        ("-3조각", "마이너스 세 조각"),
        ("+39조각", "플러스 서른아홉 조각"),
        ("+40조각", "플러스 사십 조각"),
        ("+1.5조각", "플러스 일쩜오 조각"),
        ("-1.5조각", "마이너스 일쩜오 조각"),
        ("제3조각", "제 삼조각"),
        ("제 3조각", "제 삼조각"),
        ("제4가지", "제 사가지"),
        ("제 3가지", "제 삼가지"),
        ("제40가지", "제 사십가지"),
    ],
)
def test_piece_and_kind_signed_hybrid_and_prefixed_sino(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3조에", "3조에"),
        ("제3조", "제 삼조"),
        ("제 3조", "제 삼조"),
        ("제3 조", "제 삼 조"),
        ("제 3 조", "제 삼 조"),
        ("법률 제3조", "법률 제 삼조"),
        ("제40조", "제 사십조"),
        ("제3조가", "제 삼조가"),
    ],
)
def test_prefixed_jo_reads_sino_with_space_without_unprefixed_collision(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1시방향", "한 시 방향"),
        ("1시 방향", "한 시 방향"),
        ("2시방향", "두 시 방향"),
        ("3시방향", "세 시 방향"),
        ("3시 방향", "세 시 방향"),
        ("12시방향", "열두 시 방향"),
        ("13시방향", "십삼 시 방향"),
        ("0시방향", "영 시 방향"),
        ("25시방향", "이십오 시 방향"),
        ("99시방향", "구십구 시 방향"),
        ("100시방향", "백 시 방향"),
        ("3시방향으로", "세 시 방향으로"),
        ("제3시방향", "제 삼시방향"),
        ("제 3시방향", "제 삼시방향"),
        ("제3시 방향", "제 삼시 방향"),
    ],
)
def test_clock_hour_direction_native_or_sino_always_spaced(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("제3시", "제 삼시"),
        ("제 3시", "제 삼시"),
        ("제3시간", "제 삼시간"),
        ("제 3시간", "제 삼시간"),
        ("제3시점", "제 삼시점"),
        ("제3시회의", "제 삼시회의"),
        ("제3항", "제 삼항"),
        ("제3번", "제 삼번"),
        ("제3부", "제 삼부"),
        ("제3쪽", "제 삼쪽"),
        ("제3등", "제 삼등"),
        ("제3단", "제 삼단"),
        ("제3냥", "제 삼냥"),
        ("제3자", "제 삼자"),
        ("제 3자", "제 삼자"),
        ("제3개", "제 삼개"),
        ("제 3개", "제 삼개"),
    ],
)
def test_prefixed_ordinal_always_spaces_je_and_reads_sino(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
