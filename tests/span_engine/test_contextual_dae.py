from __future__ import annotations

import pytest

from engine.main import transform, transform_debug
from engine.span_engine.numeric_dae import (
    AIRCRAFT_DAE_COUNTER_NOUNS,
    BASE_REGISTERED_DAE_COUNTER_NOUNS,
    REGISTERED_DAE_COUNTER_NOUNS,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3대2", "삼대이"),
        ("자동차 3대", "자동차 세-대"),
        ("차량 3대를 샀다", "차량 세-대를 샀다"),
        ("서버 20대", "서버 스무-대"),
        ("가업을 3대째 이어 왔다", "가업을 삼-대째 이어 왔다"),
        ("가족 3대가 함께 살았다", "가족 삼-대가 함께 살았다"),
        ("20대 남성", "이십-대 남성"),
        ("30대 초반", "삼십-대 초반"),
        ("3대 과제", "삼대 과제"),
        ("3대가 남았다", "3대가 남았다"),
        ("40대", "사십-대"),
    ],
)
def test_contextual_dae_canonical(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_dae_machine_registry_remains_exact_and_central() -> None:
    assert BASE_REGISTERED_DAE_COUNTER_NOUNS == frozenset(
        {"자동차", "차량", "장비", "버스", "서버", "카메라"}
    )
    assert REGISTERED_DAE_COUNTER_NOUNS == (
        BASE_REGISTERED_DAE_COUNTER_NOUNS | AIRCRAFT_DAE_COUNTER_NOUNS
    )
    assert transform("노트북 3대") == "노트북 3대"


@pytest.mark.parametrize(
    "noun",
    sorted(AIRCRAFT_DAE_COUNTER_NOUNS),
)
def test_registered_aircraft_nouns_use_native_dae_count(noun: str) -> None:
    assert transform(f"{noun} 8대") == f"{noun} 여덟-대"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("항공기 8대", "항공기 여덟-대"),
        ("항공기 8대를 도입했다", "항공기 여덟-대를 도입했다"),
        ("항공기는 8대", "항공기는 여덟-대"),
        ("항공기는 총 8대", "항공기는 총 여덟-대"),
        ("항공기 8대 1대를 점검했다", "항공기 여덟-대 한-대를 점검했다"),
    ],
)
def test_aircraft_dae_supported_contexts(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("제8대 항공기", "제-팔대 항공기"),
        ("8대 과제", "팔대 과제"),
        ("8대 항공기", "8대 항공기"),
        ("항공기8대", "항공기8대"),
        ("항공기 성능은 8대 1", "항공기 성능은 팔 대 일"),
        ("item_항공기_8대", "item_항공기_8대"),
    ],
)
def test_aircraft_dae_does_not_expand_other_dae_meanings(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["03대", "1,00대", "3A대"],
)
def test_contextual_dae_malformed_deferred(text: str) -> None:
    debug = transform_debug(text)
    assert debug["normalized_text"] == text
    claims = debug["debug"]["trace"]["claim_logs"]
    assert len(claims) == 1
    assert claims[0]["owner"] == "contextual_number_unit"
    assert claims[0]["claim_type"] == "preserve"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3대", "플러스 삼 대"),
        ("-3대", "마이너스 삼 대"),
        ('3.5대', '삼-쩜-오-대'),
    ],
)
def test_contextual_dae_signed_and_decimal_use_residual_reading(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "semantic_type", "decision"),
    [
        ("자동차 3대", "machine_count", "confirmed"),
        ("가업을 3대째 이어 왔다", "generation", "confirmed"),
        ("20대 남성", "age_band", "confirmed"),
        ("3대 과제", "major_item", "confirmed"),
        ("3대가 남았다", "dae_ambiguous", "deferred"),
    ],
)
def test_contextual_dae_debug(
    text: str, semantic_type: str, decision: str
) -> None:
    debug = transform_debug(text)
    logs = debug["debug"]["trace"]["contextual_decision_logs"]
    assert len(logs) == 1
    assert logs[0]["unit"] == "대"
    assert logs[0]["semantic_type"] == semantic_type
    assert logs[0]["decision"] == decision


@pytest.mark.parametrize(
    "text",
    [
        "`자동차 3대`",
        '{"value":"20대 남성"}',
        "/path/가족3대/file",
        "item_3대.json",
        "[3대 과제]",
    ],
)
def test_contextual_dae_protected(text: str) -> None:
    assert transform_debug(text)["debug"]["trace"]["contextual_decision_logs"] == []
