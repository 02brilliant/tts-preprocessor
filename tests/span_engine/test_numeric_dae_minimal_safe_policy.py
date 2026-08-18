from __future__ import annotations

import pytest

from engine.main import transform, transform_debug
from engine.span_engine.models import SourceSpan
from engine.span_engine.numeric_dae import (
    REGISTERED_DAE_COUNTER_NOUNS,
    evaluate_numeric_dae_counter_context,
    is_registered_dae_counter_noun,
)


def _debug(text: str) -> dict:
    payload = transform_debug(text)
    assert payload["ok"] is True
    assert payload["normalized_text"] == transform(text)
    return payload["debug"]


def _claims(text: str) -> list[dict]:
    return _debug(text)["trace"]["claim_logs"]


@pytest.mark.parametrize(
    ("text", "expected", "expected_span"),
    [
        ("2대1", "이대일", (0, 3)),
        ("2대 1", "이 대 일", (0, 4)),
        ("2 대 1", "이 대 일", (0, 5)),
        ("2.1대1.5", "이쩜일 대 일쩜오", (0, 7)),
        ("1/3대2/5", "삼분의 일 대 오분의 이", (0, 7)),
        ("+2대-1", "플러스 이 대 마이너스 일", (0, 5)),
        ("차량은 2대 1입니다", "차량은 이 대 일입니다", (4, 8)),
    ],
)
def test_existing_korean_dae_relations_keep_owner_and_output(
    text: str, expected: str, expected_span: tuple[int, int]
) -> None:
    assert transform(text) == expected
    claims = _claims(text)
    assert len(claims) == 1
    assert claims[0]["owner"] == "korean_da_score_pair"
    assert claims[0]["reason"] == "korean_da_score_pair_independent_right_number_gate"
    assert (
        claims[0]["span"]["start"],
        claims[0]["span"]["end"],
    ) == expected_span
    assert not any(
        claim["owner"] == "ambiguous_numeric_dae_preserve" for claim in claims
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("제2대", "제 이대"),
        ("제3대 대통령", "제 삼대 대통령"),
        ("제10대 회장", "제 십대 회장"),
    ],
)
def test_existing_prefixed_ordinal_dae_owner_is_unchanged(
    text: str, expected: str
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    claims = debug["trace"]["claim_logs"]
    assert claims[0]["owner"] == "numeric_suffix"
    assert claims[0]["reason"] == "prefixed_ordinal_numeric_suffix"
    assert not any(
        claim["owner"] == "ambiguous_numeric_dae_preserve" for claim in claims
    )
    assert all(log["passed"] for log in debug["trace"]["validation_logs"])


def test_dae_counter_noun_inventory_is_central_and_minimal() -> None:
    assert REGISTERED_DAE_COUNTER_NOUNS == frozenset(
        {"차량", "자동차", "장비", "버스", "서버", "카메라"}
    )
    assert all(
        is_registered_dae_counter_noun(noun)
        for noun in REGISTERED_DAE_COUNTER_NOUNS
    )
    assert not is_registered_dae_counter_noun("가족")


def test_context_gate_distinguishes_defer_and_owner_fallback() -> None:
    direct = evaluate_numeric_dae_counter_context(
        "차량 3대", SourceSpan(3, 5)
    )
    assert (direct.action, direct.owner, direct.reason) == (
        "DEFER_TO_COUNTER",
        "contextual_numeric_dae",
        "dae_counter_registered_noun_direct_context",
    )

    missing = evaluate_numeric_dae_counter_context("3대", SourceSpan(0, 2))
    assert (missing.action, missing.owner, missing.reason) == (
        "FALLBACK",
        "contextual_numeric_dae",
        "explicit_dae_counter_context_missing",
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("차량 3대", "차량 세 대"),
        ("장비 5대", "장비 다섯 대"),
        ("버스 10대", "버스 열 대"),
        ("서버 20대", "서버 스무 대"),
        ("차량 2대입니다", "차량 두 대입니다"),
        ("장비 3대 추가", "장비 세 대 추가"),
    ],
)
def test_registered_direct_noun_context_delegates_to_integer_counter(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    claims = _claims(text)
    dae_claim = next(
        claim for claim in claims if claim["owner"] == "contextual_number_unit"
    )
    assert dae_claim["reason"] == "contextual_number_unit_confirmed"


def test_adjacent_registered_counter_series_has_narrow_continuation() -> None:
    positive = "차량 2대 1대를 점검했다"
    assert transform(positive) == "차량 두 대 한 대를 점검했다"
    claims = [
        claim
        for claim in _claims(positive)
        if claim["owner"] == "contextual_number_unit"
    ]
    assert len(claims) == 2

    comma_boundary = "차량 2대, 가족 1대가 모였다"
    assert transform(comma_boundary) == "차량 두 대, 가족 일 대가 모였다"
    assert [claim["owner"] for claim in _claims(comma_boundary)] == [
        "contextual_number_unit",
        "contextual_number_unit",
    ]

    distant = "차량 2대를 확인했고 3대를 샀다"
    assert transform(distant) == "차량 두 대를 확인했고 3대를 샀다"
    assert [claim["owner"] for claim in _claims(distant)] == [
        "contextual_number_unit",
        "contextual_number_unit",
    ]


def test_decimal_dae_requires_the_same_explicit_context() -> None:
    positive = _debug("장비 1.5대")
    assert positive["normalized_text"] == "장비 일쩜오 대"
    decimal_claim = positive["trace"]["claim_logs"][0]
    assert decimal_claim["owner"] == "contextual_number_unit"
    assert decimal_claim["claim_type"] == "surface"

    for text, expected in (("1.5대", "일쩜오 대"), ("1.5대가", "일쩜오 대가")):
        debug = _debug(text)
        assert debug["normalized_text"] == expected
        assert [claim["owner"] for claim in debug["trace"]["claim_logs"]] == [
            "contextual_number_unit"
        ]
        assert not any(
            claim["owner"] in {"decimal", "decimal_registered_suffix"}
            for claim in debug["trace"]["claim_logs"]
        )


@pytest.mark.parametrize(
    ("text", "expected", "semantic"),
    [
        ("장비는 3.5대가 필요하다", "장비는 삼쩜오 대가 필요하다", "machine_count"),
        ("5대 과제", "오대 과제", "major_item"),
    ],
)
def test_expanded_dae_allowlist(
    text: str, expected: str, semantic: str
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    log = next(
        item
        for item in debug["trace"]["contextual_decision_logs"]
        if item["unit"] == "대"
    )
    assert log["decision"] == "confirmed"
    assert log["semantic_type"] == semantic


@pytest.mark.parametrize(
    "text",
    [
        "3대",
        "10대",
        "20대가",
        "10대 사업",
        "3대를 샀다",
        "5대가 도착했다",
        "10대를 추가했다",
    ],
)
def test_ambiguous_numeric_dae_preserves_atomically(text: str) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == text
    claims = debug["trace"]["claim_logs"]
    preserve_claims = [
        claim
        for claim in claims
        if claim["owner"] == "contextual_number_unit"
    ]
    assert preserve_claims
    assert all(claim["claim_type"] == "preserve" for claim in preserve_claims)
    assert all(
        claim["surface_type"] == "CONTEXTUAL_NUMBER_UNIT_DEFERRED_SURFACE"
        for claim in preserve_claims
    )
    assert all(
        claim["reason"] == "contextual_number_unit_deferred"
        for claim in preserve_claims
    )
    assert not any(
        claim["owner"]
        in {"number", "counter_noun", "decimal", "decimal_registered_suffix", "korean_numeric_chain"}
        for claim in claims
    )
    assert all(log["passed"] for log in debug["trace"]["validation_logs"])


def test_context_match_does_not_override_invalid_counter_numeric_core() -> None:
    debug = _debug("차량 03대")
    assert debug["normalized_text"] == "차량 03대"
    claim = debug["trace"]["claim_logs"][0]
    assert claim["owner"] == "contextual_number_unit"
    assert claim["claim_type"] == "preserve"


def test_ambiguous_numeric_dae_uses_source_exact_provenance() -> None:
    debug = _debug("20대가")
    assert [
        (piece["text"], piece["provenance"], piece["owner"])
        for piece in debug["render_pieces"]
    ] == [
        ("20", "ORIGINAL_BOUNDARY", "contextual_number_unit"),
        ("대가", "ORIGINAL_KOREAN", "contextual_number_unit"),
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[3대]", "3대"),
        ("`3대`", "`3대`"),
        ('{"value":"3대"}', '{"value":"3대"}'),
        ("path/3대/file", "path/3대/file"),
        ("A3대", "A3대"),
        ("identifier_3대", "identifier_3대"),
    ],
)
def test_protected_and_code_like_dae_keep_existing_behavior(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    assert not any(
        claim["owner"] == "ambiguous_numeric_dae_preserve"
        for claim in _claims(text)
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3명", "세 명"),
        ("3개", "세 개"),
        ("3권", "3권"),
        ("3장", "3장"),
        ("1척", "1척"),
        ("21명", "스물한 명"),
        ("40척", "사십 척"),
    ],
)
def test_other_counters_are_unchanged(text: str, expected: str) -> None:
    assert transform(text) == expected
    expected_owner = (
        "contextual_number_unit"
        if text.endswith(("척", "권", "장"))
        else "counter_noun"
    )
    assert any(
        claim["owner"] == expected_owner for claim in _claims(text)
    )


def test_mixed_numeric_dae_owner_e2e() -> None:
    text = (
        "차량 3대와 장비 1.5대를 확인했고, 20대 남성과 가족 3대는 별도 기록했으며 "
        "제3대 책임자는 경기 결과 2대1을 보고했다."
    )
    expected = (
        "차량 세 대와 장비 일쩜오 대를 확인했고, 이십 대 남성과 가족 삼 대는 별도 기록했으며 "
        "제 삼대 책임자는 경기 결과 이대일을 보고했다."
    )
    assert transform(text) == expected
    owners = [claim["owner"] for claim in _claims(text)]
    assert owners.count("contextual_number_unit") == 4
    assert "numeric_suffix" in owners
    assert "korean_da_score_pair" in owners
