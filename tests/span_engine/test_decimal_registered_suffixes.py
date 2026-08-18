from __future__ import annotations

import pytest

from engine.main import transform, transform_debug


def _transform(src: str) -> str:
    result = transform(src)
    return getattr(result, "normalized_text", result)


def _claim_owners(src: str) -> list[str]:
    result = transform_debug(src)
    trace = (result.get("debug") or {}).get("trace") or {}
    return [claim.get("owner") for claim in trace.get("claim_logs") or []]


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (
            "환자 수는 천명당 4.3명으로 집계됐습니다.",
            "환자 수는 천명당 사쩜삼 명으로 집계됐습니다.",
        ),
        (
            "이전 수치는 1.3명에서 5.9명으로 늘었습니다.",
            "이전 수치는 일쩜삼 명에서 오쩜구 명으로 늘었습니다.",
        ),
        (
            "평점 3.5점의 작품을 비교했습니다.",
            "평점 삼쩜오 점의 작품을 비교했습니다.",
        ),
        (
            "장비는 평균 2.5개였고 차량은 가구당 1.5대였습니다.",
            "장비는 평균 이쩜오 개였고 차량은 가구당 일쩜오 대였습니다.",
        ),
        (
            "책은 평균 3.2권이었고 표본은 4.7장으로 기록됐습니다.",
            "책은 평균 삼쩜이 권이었고 표본은 사쩜칠 장으로 기록됐습니다.",
        ),
        (
            "동물은 구역당 2.5마리로 조사됐습니다.",
            "동물은 구역당 이쩜오 마리로 조사됐습니다.",
        ),
        (
            "조사는 6.5건이었고 회의는 7.5회였습니다.",
            "조사는 육쩜오 건이었고 회의는 칠쩜오 회였습니다.",
        ),
    ],
)
def test_decimal_registered_counters(src: str, expected: str) -> None:
    assert _transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (
            "참가자는 3명이고 차량은 4대이며 장비는 5개입니다.",
            "참가자는 세 명이고 차량은 네 대이며 장비는 다섯 개입니다.",
        ),
        ("책은 3권이고 종이는 4장입니다.", "책은 세 권이고 종이는 네 장입니다."),
        (
            "동물은 2마리였고 의자는 6개였습니다.",
            "동물은 두 마리였고 의자는 여섯 개였습니다.",
        ),
    ],
)
def test_integer_counter_readings_unchanged(src: str, expected: str) -> None:
    assert _transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("소요 시간은 1.5분입니다.", "소요 시간은 일쩜오 분입니다."),
        ("작업은 2.5시간 걸렸습니다.", "작업은 이쩜오 시간 걸렸습니다."),
        ("기간은 3.5일입니다.", "기간은 삼쩜오 일입니다."),
        ("관찰 기간은 4.5주였습니다.", "관찰 기간은 사쩜오 주였습니다."),
        ("평균 기간은 5.5개월입니다.", "평균 기간은 오쩜오 개월입니다."),
        ("평균 보유 기간은 6.5년입니다.", "평균 보유 기간은 육쩜오 년입니다."),
    ],
)
def test_decimal_duration_time_suffixes(src: str, expected: str) -> None:
    assert _transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("길이는 1.5m입니다.", "길이는 일쩜오 미터입니다."),
        ("무게는 2.3kg입니다.", "무게는 이쩜삼 킬로그램입니다."),
        ("습도는 42.8%였습니다.", "습도는 사십이쩜팔 퍼센트였습니다."),
        ("지표는 3.5%P 하락했습니다.", "지표는 삼쩜오 퍼센트포인트 하락했습니다."),
        ("가격은 1,000.5원 올랐습니다.", "가격은 천쩜오 원 올랐습니다."),
        ("주가는 4.8배 증가했습니다.", "주가는 사쩜팔 배 증가했습니다."),
        ("점수는 2.1대1.5였습니다.", "점수는 이쩜일 대 일쩜오였습니다."),
        ("범위는 1.5~2.5명입니다.", "범위는 일쩜오에서 이쩜오 명입니다."),
    ],
)
def test_existing_decimal_owner_behaviors_unchanged(
    src: str, expected: str
) -> None:
    assert _transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (".5명", ".5명"),
        ("01.5명", "01.5명"),
        ("1.명", "1.명"),
        ("1..5명", "1..5명"),
        ("1,00.5명", "1,00.5명"),
        ("4.3명abc", "4.3명abc"),
        ("A4.3명", "A4.3명"),
    ],
)
def test_malformed_decimal_registered_suffixes_do_not_claim(
    src: str, expected: str
) -> None:
    assert "decimal_registered_suffix" not in _claim_owners(src)
    assert _transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("`4.3명`", "`4.3명`"),
        ("[4.3명]", "4.3명"),
        ("/path/4.3명/log", "/path/4.3명/log"),
        ('{"value":"4.3명"}', '{"value":"4.3명"}'),
        ("https://example.com/4.3명", "https://example.com/4.3명"),
    ],
)
def test_decimal_registered_suffixes_protected_contexts(
    src: str, expected: str
) -> None:
    assert _transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("평균은 1.5차였습니다.", "평균은 일쩜오 차였습니다."),
        ("점수는 1.5과였습니다.", "점수는 일쩜오 과였습니다."),
        ("경계는 1.5선입니다.", "경계는 일쩜오 선입니다."),
    ],
)
def test_decimal_registered_numeric_suffixes_are_spaced(
    src: str, expected: str
) -> None:
    assert _transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("4.3명으로", "사쩜삼 명으로"),
        ("3.5점의", "삼쩜오 점의"),
        ("2.5개였고", "이쩜오 개였고"),
        ("1.5대로", "일쩜오 대로"),
        ("3.5일간", "삼쩜오 일간"),
    ],
)
def test_decimal_registered_suffixes_preserve_original_tails(
    src: str, expected: str
) -> None:
    assert _transform(src) == expected
