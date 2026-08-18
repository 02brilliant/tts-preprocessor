from __future__ import annotations

import pytest

from engine.main import transform, transform_debug


def _debug(text: str) -> dict:
    payload = transform_debug(text)
    assert payload["ok"] is True
    assert payload["normalized_text"] == transform(text)
    return payload["debug"]


@pytest.mark.parametrize(
    ("text", "expected", "semantic"),
    [
        ("서류 3부를 제출했다", "서류 세 부를 제출했다", "document_copy_count"),
        ("신문 3부를 준비했다", "신문 세 부를 준비했다", "document_copy_count"),
        ("행사 3부가 시작됐다", "행사 삼부가 시작됐다", "part_or_sequence"),
        ("3부작을 공개했다", "삼부작을 공개했다", "part_or_sequence"),
        ("건물 3동을 지었다", "건물 세 동을 지었다", "building_count"),
        ("주택 3동이 무너졌다", "주택 세 동이 무너졌다", "building_count"),
        ("3동 502호", "삼 동 오백이 호", "building_identifier"),
        ("3동 주민", "삼 동 주민", "building_identifier"),
        ("피해 농가 3호를 지원했다", "피해 농가 세 호를 지원했다", "household_count"),
        ("3호실", "삼 호실", "identifier"),
        ("3호선", "삼 호선", "identifier"),
        ("열차 3호", "열차 삼 호", "identifier"),
        ("바둑 3판을 뒀다", "바둑 세 판을 뒀다", "game_count"),
        ("3판을 겨뤘다", "세 판을 겨뤘다", "game_count"),
        ("개정 3판을 냈다", "개정 삼 판을 냈다", "edition"),
        ("태권도 3단", "태권도 삼단", "grade_or_stage"),
        ("기어 3단으로 바꿨다", "기어 삼단으로 바꿨다", "grade_or_stage"),
        ("3단계부터 시작한다", "삼단계부터 시작한다", "grade_or_stage"),
        ("상자를 3단으로 쌓았다", "상자를 세 단으로 쌓았다", "stack_count"),
        ("3단 선반", "세 단 선반", "stack_count"),
        ("대회 3등을 했다", "대회 삼등을 했다", "rank_or_grade"),
        ("평가 3등급", "평가 삼등급", "rank_or_grade"),
        ("조명 3등을 설치했다", "조명 세 등을 설치했다", "light_count"),
        ("선박 3척을 샀다", "선박 세 척을 샀다", "ship_count"),
        ("길이 3척", "길이 삼 척", "length_measure"),
    ],
)
def test_batch4_exact_anchors_confirm_meaning(
    text: str, expected: str, semantic: str
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    log = next(
        log
        for log in debug["trace"]["contextual_decision_logs"]
        if log["unit"] in {"부", "동", "호", "판", "단", "등", "척"}
    )
    assert log["decision"] == "confirmed"
    assert log["semantic_type"] == semantic
    assert log["matched_anchor"]
    assert log["reentry_blocked"] is True


@pytest.mark.parametrize(
    "text",
    [
        "자료 3부",
        "3부가 남았다",
        "3동이 남았다",
        "농가 3호",
        "3호가 선정됐다",
        "3판 진행했다",
        "3단 구조",
        "3등이 남았다",
        "3척이 남았다",
    ],
)
def test_batch4_bare_or_under_anchored_surfaces_defer_atomically(
    text: str,
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == text
    contextual_claims = [
        claim
        for claim in debug["trace"]["claim_logs"]
        if claim["owner"] == "contextual_number_unit"
    ]
    assert contextual_claims
    assert all(claim["claim_type"] == "preserve" for claim in contextual_claims)
    assert not any(
        claim["owner"] in {"number", "counter_noun", "korean_numeric_chain"}
        for claim in debug["trace"]["claim_logs"]
    )


def test_batch4_apartment_identifier_allowlist() -> None:
    debug = _debug("아파트 3동")
    assert debug["normalized_text"] == "아파트 삼 동"
    log = debug["trace"]["contextual_decision_logs"][0]
    assert log["decision"] == "confirmed"
    assert log["semantic_type"] == "building_identifier"


@pytest.mark.parametrize(
    "text",
    [
        "01부",
        "1,00단",
        "3A등",
        "01척",
    ],
)
def test_batch4_malformed_surfaces_defer_without_partial_conversion(
    text: str,
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == text
    assert [claim["owner"] for claim in debug["trace"]["claim_logs"]] == [
        "contextual_number_unit"
    ]
    log = debug["trace"]["contextual_decision_logs"][0]
    assert log["decision"] == "deferred"
    assert log["blocking_reason"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3동", "플러스 삼 동"),
        ("-3호", "마이너스 삼 호"),
        ("1.5판", "일쩜오 판"),
    ],
)
def test_batch4_signed_and_decimal_use_residual_reading(
    text: str, expected: str
) -> None:
    assert _debug(text)["normalized_text"] == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/3부", "https://example.com/3부"),
        ("/tmp/3동/file", "/tmp/3동/file"),
        ('{"value":"3호"}', '{"value":"3호"}'),
        ("`3판`", "`3판`"),
        ("[3단]", "3단"),
        ("A3등", "A3등"),
        ("3척.txt", "3척.txt"),
    ],
)
def test_batch4_protected_and_identifier_surfaces_keep_precedence(
    text: str, expected: str
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    assert not any(
        log["unit"] in {"부", "동", "호", "판", "단", "등", "척"}
        for log in debug["trace"]["contextual_decision_logs"]
    )


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("제2판", "제 이판", "numeric_suffix"),
        ("제3호", "제 삼호", "numeric_suffix"),
        ("101~103호", "백일에서 백삼 호", "range"),
    ],
)
def test_batch4_existing_specific_owners_keep_precedence(
    text: str, expected: str, owner: str
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    assert any(
        claim["owner"] == owner for claim in debug["trace"]["claim_logs"]
    )
    assert not debug["trace"]["contextual_decision_logs"]


def test_batch4_multiple_meanings_and_units_can_coexist() -> None:
    text = (
        "행사 3부에 서류 2부를 냈고, 3동 502호에서 "
        "바둑 3판과 조명 4등을 설치했다."
    )
    expected = (
        "행사 삼부에 서류 두 부를 냈고, 삼 동 오백이 호에서 "
        "바둑 세 판과 조명 네 등을 설치했다."
    )
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    logs = debug["trace"]["contextual_decision_logs"]
    assert {log["unit"] for log in logs} == {"부", "동", "호", "판", "등"}
    assert all(log["decision"] == "confirmed" for log in logs)


def test_batch4_contextual_logs_remain_debug_only() -> None:
    text = "선박 3척과 길이 3척"
    assert transform(text) == "선박 세 척과 길이 삼 척"
    payload = transform_debug(text)
    assert payload["debug"]["trace"]["contextual_decision_logs"]
    assert "contextual_decision_logs" not in payload["normalized_text"]
