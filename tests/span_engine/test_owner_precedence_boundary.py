from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace
from engine.span_engine.claim_scanner import CLAIM_ORDER_DOC


def test_claim_order_documentation_snapshot() -> None:
    assert CLAIM_ORDER_DOC == (
        "bracket",
        "protected_literal",
        "corporate_marker",
        "parenthesized_hangul_alias",
        "dictionary",
        "finance_index",
        "contextual_acronym",
        "ampersand_acronym",
        "unsupported_ampersand_acronym_preserve",
        "k_hangul_lexical",
        "lexical_compound",
        "acronym_hangul_hyphen",
        "single_letter_alnum_code",
        "managed_acronym_numeric_code",
        "two_block_hyphen_code",
        "mixed_alnum_code_separator",
        "acronym_fallback",
        "contextual_malformed_number_unit",
        "contextual_large_unit_collision",
        "large_unit_atomic",
        "currency",
        "date",
        "time",
        "phone",
        "colon_semantic_pair",
        "korean_da_score_pair",
        "numeric_dae_quantity_sequence",
        "multi_colon_numeric",
        "event",
        "emergency",
        "middle_dot_numeric",
        "spaced_separator_preserve",
        "spaced_hyphen_numeric_blocks",
        "numeric_delimited_hyphen_range",
        "range",
        "hyphen_digit_blocks",
        "percent_point",
        "duration",
        "multiplier",
        "caret_literal_unit",
        "unit_contamination_preserve",
        "caret_power_unit",
        "basic_arithmetic_expression",
        "invalid_basic_arithmetic_expression_preserve",
        "fraction",
        "signed_temperature",
        "signed_degree",
        "ph",
        "signed_number",
        "compound_slash_unit",
        "compound_exact_unit",
        "special_unit",
        "simple_unit",
        "contextual_number_unit",
        "decimal_registered_suffix",
        "numeric_suffix",
        "contextual_numeric_dae",
        "ambiguous_numeric_dae_preserve",
        "invalid_signed_numeric_preserve",
        "invalid_mixed_decimal_preserve",
        "mixed_decimal_atomic",
        "decimal",
        "public_number",
        "counter_noun",
        "mixed_integer_atomic",
        "jamo",
        "administrative_suffix",
        "korean_numeric_chain",
        "number",
    )


@pytest.mark.parametrize(
    ("source", "expected_owner"),
    [
        ("K-POP", "dictionary"),
        ("K-푸드", "k_hangul_lexical"),
        ("KTX-이음", "acronym_hangul_hyphen"),
        ("K-1", "single_letter_alnum_code"),
        ("A-10C", "single_letter_alnum_code"),
        ("B-2.5", "single_letter_alnum_code"),
        ("GPT-4", "managed_acronym_numeric_code"),
        ("x-3", "two_block_hyphen_code"),
        ("제5차", "numeric_suffix"),
        ("3배", "multiplier"),
        ("112명", "counter_noun"),
        ("119건", "counter_noun"),
        ("2항목", "counter_noun"),
        ("1척", "contextual_number_unit"),
        ("29척", "contextual_number_unit"),
        ("39척", "contextual_number_unit"),
        ("40척", "contextual_number_unit"),
    ],
)
def test_critical_owner_claim_trace_snapshot(
    source: str, expected_owner: str
) -> None:
    output = transform_with_trace(source)

    assert any(claim.owner == expected_owner for claim in output.trace.claim_logs)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("K-POP", "케이팝"),
        ("K-푸드", "케이푸드"),
        ("K-뷰티", "케이뷰티"),
        ("K-팝", "케이팝"),
        ("K-2024", "K-2024"),
        ("K-ABC", "K-ABC"),
        ("K-pop", "K-pop"),
        ("K-푸드-v2", "K-푸드-v2"),
        ("K-푸드_test", "K-푸드_test"),
        ("AK-푸드", "에이케이-푸드"),
        ("model-K-푸드", "model-K-푸드"),
    ],
)
def test_k_lexical_owner_precedence_and_preserve_boundaries(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("K-1", "케이-원"),
        ("K1", "케이 원"),
        ("K-2", "케이-투"),
        ("K2", "케이 투"),
        ("K-9", "케이-나인"),
        ("K9", "케이 나인"),
        ("K-10", "케이-십"),
        ("K10", "케이 십"),
        ("K-21", "케이-이십일"),
        ("K21", "케이 이십일"),
        ("A-1", "에이-원"),
        ("A1", "에이 원"),
        ("A-10", "에이-십"),
        ("A10", "에이 십"),
        ("B-1", "비-원"),
        ("B1", "비 원"),
        ("B-10", "비-십"),
        ("B10", "비 십"),
        ("K-1.5", "케이-일쩜오"),
        ("K1.5", "케이 일쩜오"),
        ("A0.5", "에이 영쩜오"),
        ("B-2.5", "비-이쩜오"),
        ("F-15C", "에프-십오 씨"),
        ("F15C", "에프 십오 씨"),
        ("K-1A", "케이-원 에이"),
        ("K1A", "케이 원 에이"),
        ("K-21B", "케이-이십일 비"),
        ("K21B", "케이 이십일 비"),
        ("K-21BC", "케이-이십일 비씨"),
        ("A-10C", "에이-십 씨"),
        ("오늘 K-1 장비", "오늘 케이-원 장비"),
        ("장비는 F-15C입니다", "장비는 에프-십오 씨입니다"),
    ],
)
def test_single_letter_alnum_code_positive_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("AA-10", "AA-10"),
        ("AB10", "AB10"),
        ("A-10CAT", "A-10CAT"),
        ("A10CAT", "A10CAT"),
        ("A-3kg", "A-3kg"),
        ("A3kg", "A3kg"),
        ("APIv2", "APIv2"),
        ("GPU2X", "GPU2X"),
        ("USB300", "USB300"),
        ("model-X200", "model-X200"),
        ("X-200-beta", "X-200-beta"),
        ("R2D2", "R2D2"),
        ("K-2024", "K-2024"),
        ("K+1", "K+1"),
        ("K+1.5", "K+1.5"),
        ("K-+1.5", "K-+1.5"),
        ("K--1.5", "K--1.5"),
        ("K+-1.5", "K+-1.5"),
        ("K-ABC", "K-ABC"),
        ("K-pop", "K-pop"),
        ("AK-1", "AK-1"),
        ("model-K1", "model-K1"),
        ("model-K-1", "model-K-1"),
        ("https://example.com/K-1", "https://example.com/K-1"),
        ("docs/K-1/report.md", "docs/K-1/report.md"),
    ],
)
def test_single_letter_alnum_code_preserve_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("B-2.5", "비-이쩜오"),
        ("x-3", "엑스-삼"),
        ("B-2.5beta", "B-2.5beta"),
        ("x-2.5℉", "x-2.5℉"),
        ("A-10C", "에이-십 씨"),
        ("A-3kg", "A-3kg"),
        ("1-2", "1-2"),
        ("3-2", "3-2"),
        ("1-1 무", "1-1 무"),
    ],
)
def test_hyphen_code_and_single_letter_alnum_interactions(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("제5차", "제 오차"),
        ("제 5차", "제 오차"),
        ("제15권", "제 십오권"),
        ("제 15권", "제 십오권"),
        ("제2편", "제 이편"),
        ("제 2편", "제 이편"),
        ("제2판", "제 이판"),
        ("제2줄", "제 이줄"),
        ("제2칸", "제 이칸"),
        ("A제5차", "A제5차"),
        ("A제 5차", "A제 5차"),
        ("제5G", "제5G"),
        ("제5abc", "제5abc"),
        ("제5-차", "제5-차"),
        ("제2항목", "제 이항목"),
        ("제2사례", "제 이사례"),
        ("제2대", "제 이대"),
        ("제2문항", "제 이문항"),
        ("2차례", "두 차례"),
        ("31차례", "서른한 차례"),
        ("101차례", "백일 차례"),
        ("2차례abc", "2차례abc"),
    ],
)
def test_ordinal_numeric_suffix_and_counter_collision_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("39명", "서른아홉 명"),
        ("40명", "사십 명"),
        ("99명", "구십구 명"),
        ("100명", "백 명"),
        ("101명", "백일 명"),
        ("112명", "백십이 명"),
        ("139명", "백삼십구 명"),
        ("140명", "백사십 명"),
        ("39건", "서른아홉 건"),
        ("40건", "사십 건"),
        ("99건", "구십구 건"),
        ("100건", "백 건"),
        ("101건", "백일 건"),
        ("119건", "백십구 건"),
        ("139건", "백삼십구 건"),
        ("140건", "백사십 건"),
        ("39편", "39편"),
        ("40편", "40편"),
        ("101편", "101편"),
        ("140편", "140편"),
        ("2대", "2대"),
        ("39대", "39대"),
        ("40대", "사십 대"),
        ("101대", "백일 대"),
        ("2항목", "두 항목"),
        ("40항목", "사십 항목"),
        ("101항목", "백일 항목"),
        ("1척", "1척"),
        ("29척", "29척"),
        ("39척", "39척"),
        ("40척", "40척"),
        ("100척", "100척"),
        ("2항목abc", "2항목abc"),
        ("1척abc", "1척abc"),
        ("A2항목", "A2항목"),
        ("A1척", "A1척"),
        ("model-1척", "model-1척"),
        ("긴급번호 112는", "긴급번호 일일이는"),
        ("화재가 나면 119에", "화재가 나면 일일구에"),
    ],
)
def test_counter_threshold_100_plus_sino_and_emergency_split_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("110명", "백십명"),
        ("120명", "백이십명"),
        ("1339명", "천삼백삼십구명"),
        ("112명", "백십이 명"),
        ("119건", "백십구 건"),
    ],
)
def test_public_number_ambiguity_and_counter_fallback_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize("source", ["1척abc", "A1척", "model-1척"])
def test_ship_counter_unsafe_forms_do_not_claim_counter_owner(source: str) -> None:
    output = transform_with_trace(source)

    assert output.normalized_text == source
    assert not any(claim.owner == "counter_noun" for claim in output.trace.claim_logs)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("6월", "유월"),
        ("10월", "시월"),
        ("2026년 6월 17일", "이천이십육년 유월 십칠일"),
        ("2025-01-03", "이천이십오년 일월 삼일"),
        ("2025/10/21", "이천이십오년 시월 이십일일"),
        ("2025-13-03", "이공이오 일삼 공삼"),
        ("2025-01-32", "이공이오 공일 삼이"),
        ("6~10월", "유월에서 시월"),
        ("1~11월", "일월에서 십일월"),
        ("2~3시", "두 시에서 세 시"),
        ("7~9시간", "일곱 시간에서 아홉 시간"),
        ("20~22시간", "스무 시간에서 스물두 시간"),
    ],
)
def test_date_month_and_range_precedence_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "K-푸드 https://example.com/K-푸드 6월",
            "케이푸드 https://example.com/K-푸드 유월",
        ),
        (
            "docs/K-1/report.md와 K-1 장비",
            "docs/K-1/report.md와 케이-원 장비",
        ),
        (
            "user@example.com에게 112명 명단 전달",
            "user@example.com에게 백십이 명 명단 전달",
        ),
        (
            "C:/Users/test/K-푸드/file.txt와 K-뷰티",
            "C:/Users/test/K-푸드/file.txt와 케이뷰티",
        ),
    ],
)
def test_protected_span_internal_preserve_and_adjacent_transform_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected
