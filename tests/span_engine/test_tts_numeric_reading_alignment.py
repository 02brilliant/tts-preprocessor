from __future__ import annotations

import pytest

from engine.main import transform, transform_debug


def _debug(text: str) -> dict:
    payload = transform_debug(text)
    assert payload["ok"] is True
    assert payload["normalized_text"] == transform(text)
    return payload["debug"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.12", "십이쩜일이"),
        ("307.16", "삼백칠쩜일육"),
        ("7443.28", "칠천사백사십삼쩜이팔"),
        ("7443.28에", "칠천사백사십삼쩜이팔에"),
        ("2025.01", "이천이십오쩜영일"),
        ("2025.13", "이천이십오쩜일삼"),
    ],
)
def test_two_block_dotted_numbers_default_to_decimal(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    claims = _debug(text)["trace"]["claim_logs"]
    assert any(
        claim["owner"] == "decimal"
        and claim["reason"] == "decimal_match"
        for claim in claims
    )
    assert not any(
        claim["reason"] == "short_dotted_year_month_preserve"
        for claim in claims
    )



@pytest.mark.parametrize(
    "text",
    [".5", "5..2", "3..140", "25..50"],
)
def test_malformed_dotted_numbers_preserve_atomically(text: str) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == text
    assert [
        (claim["owner"], claim["reason"])
        for claim in debug["trace"]["claim_logs"]
    ] == [("preserve", "malformed_dotted_numeric_preserve")]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/v/7443.28", "https://example.com/v/7443.28"),
        ("/tmp/7443.28/report", "/tmp/7443.28/report"),
        ("report-7443.28.txt", "report-7443.28.txt"),
        ("[7443.28]", "7443.28"),
        ("[5만1839.26]", "5만1839.26"),
        ("https://example.com/5만1839.26", "https://example.com/5만1839.26"),
        ("/path/5만1839.26/log", "/path/5만1839.26/log"),
    ],
)
def test_dotted_and_large_unit_protected_contexts(
    text: str, expected: str
) -> None:
    assert transform(text) == expected

def test_two_block_dotted_specific_owner_boundaries() -> None:
    leading_zero = _debug("05.03")
    assert leading_zero["normalized_text"] == "05.03"
    assert [
        (claim["owner"], claim["reason"])
        for claim in leading_zero["trace"]["claim_logs"]
    ] == [("preserve", "leading_zero_malformed_decimal_preserve")]

    code_context = _debug("버전 2025.01")
    assert code_context["normalized_text"] == "버전 2025.01"
    assert any(
        claim["owner"] == "preserve"
        and claim["reason"] == "short_dotted_code_context_preserve"
        for claim in code_context["trace"]["claim_logs"]
    )

    event = _debug("12.12 사태")
    assert event["normalized_text"] == "십이십이 사태"
    assert any(
        claim["owner"] == "event"
        and claim["reason"] == "event_keyword_gate"
        for claim in event["trace"]["claim_logs"]
    )

    fallback = _debug("12.12 수치")
    assert fallback["normalized_text"] == "십이쩜일이 수치"
    assert any(claim["owner"] == "decimal" for claim in fallback["trace"]["claim_logs"])


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2025.01.03", "이천이십오년 일월 삼일"),
        ("2025.13.03", "이공이오쩜 일삼쩜 공삼"),
        ("12.12.1990", "12.12.1990"),
        ("v1.2.3", "v1.2.3"),
        ("docs/2025.01.03/report.md", "docs/2025.01.03/report.md"),
        ("[2025.01.03]", "2025.01.03"),
    ],
)
def test_three_or_more_dotted_blocks_keep_existing_routing(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5만1839.26", "오만천팔백삼십구쩜이육"),
        ("5만1839.26에", "오만천팔백삼십구쩜이육에"),
        ("2만5508.07", "이만오천오백팔쩜영칠"),
        ("2만5508.07에", "이만오천오백팔쩜영칠에"),
        ("5만1839", "오만천팔백삼십구"),
        ("3.5만", "삼쩜오 만"),
    ],
)
def test_structured_compact_large_unit_decimal_and_regressions(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "5만1839.",
        "5만01839.26",
        "5만1,839.2.6",
        "5만1839.26abc",
        "A5만1839.26",
        "`5만1839.26`",
    ],
)
def test_invalid_or_code_like_compact_large_unit_decimal_preserves(text: str) -> None:
    assert transform(text) == text


def test_structured_compact_large_unit_trace_and_provenance() -> None:
    text = "5만1839.26에"
    debug = _debug(text)
    claims = debug["trace"]["claim_logs"]
    assert [
        (
            claim["owner"],
            claim["reason"],
            claim["span"]["start"],
            claim["span"]["end"],
        )
        for claim in claims
    ] == [
        (
            "large_unit_atomic",
            "large_unit_structured_decimal_surface",
            0,
            len("5만1839.26"),
        )
    ]

    pieces = debug["render_pieces"]
    assert [
        (
            piece["text"],
            piece["provenance"],
            piece["source_span"]["start"],
            piece["source_span"]["end"],
        )
        for piece in pieces
    ] == [
        ("오", "GENERATED_READING", 0, 1),
        ("만", "ORIGINAL_KOREAN", 1, 2),
        ("천팔백삼십구쩜이육", "GENERATED_READING", 2, 9),
        ("에", "ORIGINAL_KOREAN", 9, 10),
    ]
    assert all(
        log["passed"] is True for log in debug["trace"]["validation_logs"]
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("다우존스30", "다우존스삼십"),
        ("5극3특", "오극삼특"),
        ("5극 3특", "오극 삼특"),
        ("한1글", "한일글"),
        ("다우존스30과 5극3특", "다우존스삼십과 오극삼특"),
    ],
)
def test_korean_numeric_chain_reads_only_ascii_integer_cores(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "A1한2",
        "abc119",
        "한1글_id",
        "ㄱ한1글",
        "한1글/경로",
        "`5극3특`",
        '{"값":"한1글"}',
    ],
)
def test_korean_numeric_chain_rejects_code_like_tokens(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("3대", "3대", "contextual_number_unit"),
        ("제15권", "제 십오권", "numeric_suffix"),
        ("종로3가", "종로 삼 가", "administrative_suffix"),
    ],
)
def test_specific_numeric_owners_precede_korean_numeric_chain(
    text: str, expected: str, owner: str
) -> None:
    debug = _debug(text)
    assert debug["normalized_text"] == expected
    assert any(claim["owner"] == owner for claim in debug["trace"]["claim_logs"])
    assert not any(
        claim["owner"] == "korean_numeric_chain"
        for claim in debug["trace"]["claim_logs"]
    )


def test_korean_numeric_chain_trace_and_provenance() -> None:
    debug = _debug("5극3특")
    assert [
        (claim["owner"], claim["reason"], claim["span"]["start"], claim["span"]["end"])
        for claim in debug["trace"]["claim_logs"]
    ] == [
        ("korean_numeric_chain", "korean_numeric_chain_full_consume", 0, 4)
    ]
    assert [
        (piece["text"], piece["provenance"])
        for piece in debug["render_pieces"]
    ] == [
        ("오", "GENERATED_READING"),
        ("극", "ORIGINAL_KOREAN"),
        ("삼", "GENERATED_READING"),
        ("특", "ORIGINAL_KOREAN"),
    ]
    assert all(
        log["passed"] is True for log in debug["trace"]["validation_logs"]
    )


def test_full_news_numeric_regression_via_official_transform() -> None:
    text = (
        "뉴욕증시에서 다우존스30 산업평균지수는 전장보다 307.16포인트 내린 "
        "5만1839.26에 거래를 마쳤다. S&P 500 지수는 전장보다 14.41포인트 내린 "
        "7443.28에, 기술주 중심의 나스닥 종합지수는 전장보다 12.17포인트 내린 "
        "2만5508.07에 각각 마감했다. 5극3특, 5극 3특 3대 프로젝트 시작합니다."
    )
    expected = (
        "뉴욕증시에서 다우존스삼십 산업평균지수는 전장보다 삼백칠쩜일육포인트 내린 "
        "오만천팔백삼십구쩜이육에 거래를 마쳤다. 에스앤피 오백 지수는 전장보다 "
        "십사쩜사일포인트 내린 칠천사백사십삼쩜이팔에, 기술주 중심의 나스닥 "
        "종합지수는 전장보다 십이쩜일칠포인트 내린 이만오천오백팔쩜영칠에 각각 "
        "마감했다. 오극삼특, 오극 삼특 3대 프로젝트 시작합니다."
    )
    assert transform(text) == expected
