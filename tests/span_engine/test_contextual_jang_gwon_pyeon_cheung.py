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
        ("사진 3장을 골랐다", "사진 세 장을 골랐다", "sheet_count"),
        ("종이 4장", "종이 네 장", "sheet_count"),
        ("3장 2절", "삼 장 이절", "chapter_number"),
        ("책 3장을 읽었다", "책 삼 장을 읽었다", "chapter_number"),
        ("책 3권을 샀다", "책 세 권을 샀다", "book_count"),
        ("도서 4권", "도서 네 권", "book_count"),
        ("3권 2호", "삼 권 이 호", "volume_number"),
        ("시리즈 3권", "시리즈 삼 권", "volume_number"),
        ("영화 3편을 봤다", "영화 세 편을 봤다", "work_count"),
        ("논문 4편을 발표했다", "논문 네 편을 발표했다", "work_count"),
        ("시리즈 3편", "시리즈 삼 편", "part_number"),
        ("법전 3편", "법전 삼 편", "part_number"),
        ("3층 회의실", "삼 층 회의실", "floor_location"),
        ("3층에 산다", "삼 층에 산다", "floor_location"),
        ("3층에서 만났다", "삼 층에서 만났다", "floor_location"),
        ("지하 3층", "지하 삼 층", "floor_location"),
        ("지상 3층", "지상 삼 층", "floor_location"),
        (
            "지하 1층부터 지상 3층까지",
            "지하 일 층부터 지상 삼 층까지",
            "floor_location",
        ),
        ("지상3층", "지상삼 층", "floor_location"),
    ],
)
def test_batch5_exact_anchors_confirm_meaning(
    text: str, expected: str, semantic: str
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    log = next(
        log
        for log in debug["trace"]["contextual_decision_logs"]
        if log["unit"] in {"장", "권", "편", "층"}
    )
    assert log["decision"] == "confirmed"
    assert log["semantic_type"] == semantic
    assert log["matched_anchor"]
    assert log["reentry_blocked"] is True


def test_basement_to_above_ground_floor_span_confirms_both_floors() -> None:
    debug = _debug("지하 1층부터 지상 3층까지")
    assert debug["normalized_text"] == "지하 일 층부터 지상 삼 층까지"
    cheung_logs = [
        log
        for log in debug["trace"]["contextual_decision_logs"]
        if log["unit"] == "층"
    ]
    assert [log["decision"] for log in cheung_logs] == ["confirmed", "confirmed"]
    assert {log["matched_anchor"] for log in cheung_logs} == {
        "location_prefix:지하",
        "location_prefix:지상",
    }


@pytest.mark.parametrize(
    "text",
    [
        "3장부터 읽었다",
        "3장이 중요하다",
        "3권부터 읽었다",
        "3권이 남았다",
        "3편부터 공개한다",
        "3편이 남았다",
        "3층을 올라갔다",
        "3층을 내려갔다",
        "3층이 무너졌다",
        "건물은 3층이다",
        "1층부터 3층까지",
    ],
)
def test_batch5_bare_or_ambiguous_surfaces_defer_atomically(text: str) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == text
    claims = [
        claim
        for claim in debug["trace"]["claim_logs"]
        if claim["owner"] == "contextual_number_unit"
    ]
    assert claims
    assert all(claim["claim_type"] == "preserve" for claim in claims)
    assert not any(
        claim["owner"] in {"counter_noun", "number", "korean_numeric_chain"}
        for claim in debug["trace"]["claim_logs"]
    )


@pytest.mark.parametrize(
    "text",
    ["01장", "1,00장", "3A권"],
)
def test_batch5_malformed_surfaces_defer_without_partial_conversion(
    text: str,
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == text
    assert [claim["owner"] for claim in debug["trace"]["claim_logs"]] == [
        "contextual_number_unit"
    ]
    assert debug["trace"]["contextual_decision_logs"][0]["decision"] == "deferred"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3권", "플러스 삼 권"),
        ("-3편", "마이너스 삼 편"),
        ("1.5층", "일쩜오 층"),
    ],
)
def test_batch5_signed_and_decimal_use_residual_reading(
    text: str, expected: str
) -> None:
    assert _debug(text)["normalized_text"] == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/3장", "https://example.com/3장"),
        ("/tmp/3권/file", "/tmp/3권/file"),
        ('{"value":"3편"}', '{"value":"3편"}'),
        ("`3층`", "`3층`"),
        ("[3장]", "3장"),
        ("A3권", "A3권"),
        ("3편.txt", "3편.txt"),
    ],
)
def test_batch5_protected_and_identifier_surfaces_keep_precedence(
    text: str, expected: str
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    assert not any(
        log["unit"] in {"장", "권", "편", "층"}
        for log in debug["trace"]["contextual_decision_logs"]
    )


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("제3장", "제 삼장", "numeric_suffix"),
        ("제15권", "제 십오권", "numeric_suffix"),
        ("제2편", "제 이편", "numeric_suffix"),
        ("1~3층", "일에서 삼 층", "range"),
        ("12-15장", "십이에서 십오 장", "range"),
    ],
)
def test_batch5_existing_ordinal_and_range_owners_keep_precedence(
    text: str, expected: str, owner: str
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    assert any(
        claim["owner"] == owner for claim in debug["trace"]["claim_logs"]
    )
    assert not debug["trace"]["contextual_decision_logs"]


def test_batch5_multiple_meanings_can_coexist() -> None:
    text = (
        "사진 3장과 책 2권, 영화 4편을 챙겨 "
        "3층 회의실에서 책 3장을 읽었다."
    )
    expected = (
        "사진 세 장과 책 두 권, 영화 네 편을 챙겨 "
        "삼 층 회의실에서 책 삼 장을 읽었다."
    )
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    logs = debug["trace"]["contextual_decision_logs"]
    assert {log["unit"] for log in logs} == {"장", "권", "편", "층"}
    assert all(log["decision"] == "confirmed" for log in logs)
