from __future__ import annotations

import pytest

from engine.main import transform, transform_debug


@pytest.mark.parametrize("text", ["1-2", "3-2", "4-3", "12-15", "10-20", "123-456"])
def test_bare_compact_two_block_hyphen_preserves_atomically(text: str) -> None:
    assert transform(text) == text
    claims = _claims(text)
    assert len(claims) == 1
    assert claims[0]["owner"] == "preserve"
    assert claims[0]["reason"] == "invalid_basic_arithmetic_expression_preserve"
    assert claims[0]["span"] == {"start": 0, "end": len(text), "length": len(text)}
    assert not _has_numeric_reentry(claims)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3-2+1", "삼 빼기 이 더하기 일"),
        ("2×4-3", "이 곱하기 사 빼기 삼"),
        ("2x4-3", "이 곱하기 사 빼기 삼"),
        ("8÷2-1", "팔 나누기 이 빼기 일"),
        ('3.2-1.1+2', '삼-쩜-이 빼기 일-쩜-일 더하기 이'),
        ("-4-3+2", "마이너스 사 빼기 삼 더하기 이"),
    ],
)
def test_mixed_operator_expression_allows_compact_binary_minus(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    _assert_arithmetic_full_claim(text, requires_equality=False)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4-3=1", "사 빼기 삼은 일"),
        ("2×4-3=5", "이 곱하기 사 빼기 삼은 오"),
        ("10-3=7", "십 빼기 삼은 칠"),
        ('3.2-1.1=2.1', '삼-쩜-이 빼기 일-쩜-일은 이-쩜-일'),
        ("-4-3=-7", "마이너스 사 빼기 삼은 마이너스 칠"),
    ],
)
def test_single_equality_allows_compact_binary_minus(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    _assert_arithmetic_full_claim(text, requires_equality=True)


def test_pure_compact_hyphen_chain_keeps_existing_digit_block_owner() -> None:
    text = "10-3-2"
    assert transform(text) == "일공 삼 이"
    claims = _claims(text)
    assert len(claims) == 1
    assert claims[0]["owner"] == "hyphen_digit_blocks"
    assert claims[0]["reason"] == "hyphen_digit_block_route"
    assert not any(claim["owner"] == "basic_arithmetic_expression" for claim in claims)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3 - 4", "삼 빼기 사"),
        ('3.2 - 5.7', '삼-쩜-이 빼기 오-쩜-칠'),
        ("-3 - -4", "마이너스 삼 빼기 마이너스 사"),
        ('+3.4 - -2.3', '플러스 삼-쩜-사 빼기 마이너스 이-쩜-삼'),
    ],
)
def test_exact_spaced_subtraction_remains_arithmetic(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    _assert_arithmetic_full_claim(text, requires_equality=False)


@pytest.mark.parametrize("text", ["3- 4", "3 -4"])
def test_asymmetric_binary_minus_spacing_preserves_atomically(text: str) -> None:
    assert transform(text) == text
    claims = _claims(text)
    assert len(claims) == 1
    assert claims[0]["owner"] == "preserve"
    assert claims[0]["reason"] == "invalid_basic_arithmetic_expression_preserve"
    assert not _has_numeric_reentry(claims)


def test_supported_short_hyphen_year_month_keeps_existing_preserve() -> None:
    text = "2025-01"
    assert transform(text) == text
    assert not any(
        claim["owner"] in {"basic_arithmetic_expression", "hyphen_digit_blocks"}
        for claim in _claims(text)
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("01-02", "공일 공이"),
        ("001-23", "공공일 이삼"),
        ("12-034", "일이 공삼사"),
        ("00-10", "공공 일공"),
        ("1234-56", "일이삼사 오육"),
        ("12-3456", "일이 삼사오육"),
        ("123-4567", "일이삼 사오육칠"),
    ],
)
def test_two_block_numeric_code_separator_precedes_arithmetic(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    claims = _claims(text)
    assert len(claims) == 1
    assert claims[0]["owner"] == "hyphen_digit_blocks"
    assert claims[0]["reason"] == "two_block_numeric_code_separator_route"


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("010-1234-5678", "공일공 일이삼사 오육칠팔", "hyphen_digit_blocks"),
        ("123-456-7890", "일이삼 사오육 칠팔구공", "hyphen_digit_blocks"),
        ("1-1-9", "일 일 구", "hyphen_digit_blocks"),
        ("12-34-56", "일이 삼사 오육", "hyphen_digit_blocks"),
        ("1234-5678", "일이삼사 오육칠팔", "phone"),
        ("2026-0417", "이공이육 공사일칠", "phone"),
        ("2025-01-03", "이천이십오년 일월 삼일", "date"),
        ("2025-13-03", "이공이오 일삼 공삼", "date"),
        ("1-2kg", "일에서 이-킬로그램", "range_with_unit"),
        ("3-5km", "삼에서 오-킬로미터", "range_with_unit"),
        ('B-2.5', '비-이-쩜-오', "single_letter_alnum_code"),
        ('A-3.14', '에이-삼-쩜-일사', "single_letter_alnum_code"),
        ("x-3", "엑스-삼", "two_block_hyphen_code"),
        ('가-3.14', '가-삼-쩜-일사', "two_block_hyphen_code"),
        ('ㄱ-2.5', '기역-이-쩜-오', "two_block_hyphen_code"),
        ("GPT-4", "지피티-포", "managed_acronym_numeric_code"),
        ('version-1.5', '버전-일-쩜-오', "managed_acronym_numeric_code"),
        ('K-1.5', '케이-일-쩜-오', "single_letter_alnum_code"),
    ],
)
def test_existing_hyphen_structured_owners_remain_authoritative(
    text: str, expected: str, owner: str
) -> None:
    assert transform(text) == expected
    claims = _claims(text)
    assert any(claim["owner"] == owner for claim in claims)
    assert not any(claim["owner"] == "basic_arithmetic_expression" for claim in claims)


@pytest.mark.parametrize("text", ["+1.5-2kg", "-1.5-2kg"])
def test_signed_hyphen_range_keeps_existing_atomic_preserve(text: str) -> None:
    assert transform(text) == text
    claims = _claims(text)
    assert len(claims) == 1
    assert claims[0]["reason"] == "signed_numeric_delimited_range_disallowed_delimiter_preserve"
    assert not _has_numeric_reentry(claims)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/path/1-2/log", "/path/1-2/log"),
        ("https://example.com/1-2", "https://example.com/1-2"),
        ("user+1-2@example.com", "user+1-2@example.com"),
        ('{"value":"1-2"}', '{"value":"1-2"}'),
        ("`1-2`", "`1-2`"),
        ("[1-2]", "1-2"),
        ("C++17", "C++17"),
        ("A+B", "A+B"),
        ("a+=1", "a+=1"),
    ],
)
def test_protected_hyphen_contexts_block_arithmetic_reentry(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    claims = _claims(text)
    assert not any(claim["owner"] == "basic_arithmetic_expression" for claim in claims)


def test_hangul_code_left_keeps_original_provenance_and_shadow_validation() -> None:
    debug = transform_debug("가-3.14")["debug"]
    assert debug["normalized_text"] == "가-삼-쩜-일사"
    pieces = debug["render_pieces"]
    assert [(piece["text"], piece["provenance"]) for piece in pieces] == [
        ("가", "ORIGINAL_KOREAN"),
        ("-", "ORIGINAL_BOUNDARY"),
        ("삼-쩜-일사", "GENERATED_READING"),
    ]
    assert all(log["passed"] for log in debug["trace"]["validation_logs"])


def _assert_arithmetic_full_claim(text: str, *, requires_equality: bool) -> None:
    debug = transform_debug(text)["debug"]
    trace = debug["trace"]
    claims = trace["claim_logs"]
    assert len(claims) == 1
    claim = claims[0]
    assert claim["owner"] == "basic_arithmetic_expression"
    assert claim["reason"] == "basic_arithmetic_expression_full_consume_gate"
    assert claim["span"] == {"start": 0, "end": len(text), "length": len(text)}
    parser_log = next(
        log for log in trace["parser_logs"] if log["owner"] == claim["owner"]
    )
    assert "SUBTRACT" in parser_log["metadata"]["operator_kinds"]
    assert parser_log["metadata"]["has_equality"] is requires_equality
    assert all(log["passed"] for log in trace["validation_logs"])


def _claims(text: str) -> list[dict[str, object]]:
    debug = transform_debug(text)["debug"]
    trace = debug.get("trace") or {}
    return trace.get("claim_logs", [])


def _has_numeric_reentry(claims: list[dict[str, object]]) -> bool:
    return any(
        claim["owner"]
        in {
            "basic_arithmetic_expression",
            "signed_number",
            "fraction",
            "decimal",
            "number",
        }
        for claim in claims
    )
