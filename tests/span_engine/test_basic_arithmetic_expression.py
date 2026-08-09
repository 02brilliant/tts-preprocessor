from __future__ import annotations

import pytest

from engine.main import transform, transform_debug
from engine.span_engine.arithmetic import parse_basic_arithmetic_expression_at


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3+4", "삼 더하기 사"),
        ("3 - 4", "삼 빼기 사"),
        ("4.5x3", "사쩜오 곱하기 삼"),
        ("4.5 x 3", "사쩜오 곱하기 삼"),
        ("4.5×3", "사쩜오 곱하기 삼"),
        ("8÷2", "팔 나누기 이"),
        ("8 ÷ 2", "팔 나누기 이"),
    ],
)
def test_basic_arithmetic_operators(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["3+4", "3 +4", "3+ 4", "3 + 4"])
def test_basic_arithmetic_allows_at_most_one_ascii_space(text: str) -> None:
    assert transform(text) == "삼 더하기 사"


@pytest.mark.parametrize("text", ["3  + 4", "3\t+\t4", "3\n+\n4"])
def test_basic_arithmetic_rejects_other_operator_spacing(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3+4", "플러스 삼 더하기 사"),
        ("-3+4", "마이너스 삼 더하기 사"),
        ("3 + -4", "삼 더하기 마이너스 사"),
        ("-3 - -4", "마이너스 삼 빼기 마이너스 사"),
        ("+3.4 x -2.3", "플러스 삼쩜사 곱하기 마이너스 이쩜삼"),
        ("-2x+3", "마이너스 이 곱하기 플러스 삼"),
    ],
)
def test_basic_arithmetic_distinguishes_unary_and_binary_signs(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["++3+4", "3++4", "3+-+4", "- 3+4"])
def test_basic_arithmetic_rejects_conflicting_signs(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.50+2.05", "일쩜오영 더하기 이쩜영오"),
        ("1,000+2,000", "천 더하기 이천"),
        ("1,000.50 - 500.25", "천쩜오영 빼기 오백쩜이오"),
    ],
)
def test_basic_arithmetic_reuses_decimal_and_comma_canonical(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["03+4", ".5+2", "3.+2", "1,00+2", "1.2.3+4"],
)
def test_basic_arithmetic_invalid_numeric_operand_preserves_atomically(
    text: str,
) -> None:
    assert transform(text) == text
    claims = _claim_logs(text)
    preserve = next(
        claim
        for claim in claims
        if claim["reason"] == "invalid_basic_arithmetic_expression_preserve"
    )
    assert preserve["span"]["start"] == 0
    assert preserve["span"]["end"] == len(text)
    assert not any(
        claim["owner"] in {"signed_number", "decimal", "number"}
        for claim in claims
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1/3+2/3", "삼분의 일 더하기 삼분의 이"),
        ("-1/3 × 3", "마이너스 삼분의 일 곱하기 삼"),
        ("1/2+1/2=1", "이분의 일 더하기 이분의 일은 일"),
        ("8/2", "이분의 팔"),
    ],
)
def test_basic_arithmetic_reuses_fraction_policy(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["1 / 3 + 2", "1.5/3 + 2", "1/0 + 2"])
def test_invalid_fraction_operand_preserves_whole_expression(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3+4=7", "삼 더하기 사는 칠"),
        ("3+6=9", "삼 더하기 육은 구"),
        ("1.2+3.5=4.7", "일쩜이 더하기 삼쩜오는 사쩜칠"),
        ("3-5=-2", "삼 빼기 오는 마이너스 이"),
        ("2+2=5", "이 더하기 이는 오"),
    ],
)
def test_basic_arithmetic_equals_generates_eun_neun(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["3=3=3", "3==3", "3+=4"])
def test_basic_arithmetic_rejects_multiple_or_compound_equals(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2+3×4", "이 더하기 삼 곱하기 사"),
        ("2×3-1+4", "이 곱하기 삼 빼기 일 더하기 사"),
        ("2×3+4=10", "이 곱하기 삼 더하기 사는 십"),
    ],
)
def test_basic_arithmetic_reads_chains_without_calculation(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["x+3", "3x", "x2", "max3", "3xabc"])
def test_numeric_x_boundary_preserves_non_expression_tokens(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "3*4",
        "3X4",
        "3kg+4kg",
        "+25℃-3℃",
        "1,000원+2,000원",
        "(3+4)×2",
        "2^3",
        "sqrt(4)",
    ],
)
def test_unsupported_operators_and_operands_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "protected_raw"),
    [
        ("식은 (3+4)×2다", "(3+4)×2"),
        ("식은 sqrt(4)다", "sqrt(4)"),
    ],
)
def test_unsupported_parenthesized_arithmetic_preserves_inside_korean_sentence(
    text: str, protected_raw: str
) -> None:
    assert transform(text) == text
    start = text.index(protected_raw)
    end = start + len(protected_raw)
    claims = _claim_logs(text)
    preserve = next(
        claim
        for claim in claims
        if claim["owner"] == "preserve"
        and claim["reason"] == "url_path_email_code_protection_claim"
        and claim["span"]["start"] == start
        and claim["span"]["end"] == end
    )
    assert preserve["surface_type"] == "PROTECTED_LITERAL_SURFACE"
    assert not any(
        claim["owner"]
        in {
            "basic_arithmetic_expression",
            "signed_number",
            "fraction",
            "decimal",
            "number",
        }
        and claim["span"]["start"] < end
        and start < claim["span"]["end"]
        for claim in claims
    )


@pytest.mark.parametrize(
    "text",
    ["C++17", "A+B", "x+y=3", "a+=1", "file/path"],
)
def test_no_hangul_gate_keeps_non_numeric_code_and_paths(text: str) -> None:
    assert transform(text) == text


def test_registered_managed_code_still_wins_over_arithmetic_negative_gate() -> None:
    assert transform("version-2") == "버전-투"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+25℃", "영상 이십오도"),
        ("-25℃", "영하 이십오도"),
        ("+3.4", "플러스 삼쩜사"),
        ("-2.3", "마이너스 이쩜삼"),
        ("1/3", "삼분의 일"),
        ("-1/3", "마이너스 삼분의 일"),
        ("2025/01/03", "이천이십오년 일월 삼일"),
        ("15.2km/L", "리터당 십오쩜이 킬로미터"),
        ("/path/3+4/log", "/path/3+4/log"),
        ("https://example.com?q=3+4", "https://example.com?q=3+4"),
        ('{"expr":"3+4"}', '{"expr":"3+4"}'),
        ("`3+4`", "`3+4`"),
        ("[3+4]", "3+4"),
        ("1234-5678", "일이삼사 오육칠팔"),
    ],
)
def test_arithmetic_owner_preserves_existing_structured_and_protected_routing(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_basic_arithmetic_trace_and_render_provenance() -> None:
    debug = transform_debug("+3.4 x -2.3")["debug"]
    trace = debug["trace"]
    claim = next(
        entry
        for entry in trace["claim_logs"]
        if entry["owner"] == "basic_arithmetic_expression"
    )
    assert claim["surface_type"] == "BASIC_ARITHMETIC_EXPRESSION_SURFACE"
    assert claim["reason"] == "basic_arithmetic_expression_full_consume_gate"
    assert claim["span"] == {"start": 0, "end": 11, "length": 11}

    parser_log = next(
        entry
        for entry in trace["parser_logs"]
        if entry["owner"] == "basic_arithmetic_expression"
    )
    assert parser_log["metadata"]["operand_kinds"] == [
        "SIGNED_NUMBER",
        "SIGNED_NUMBER",
    ]
    assert parser_log["metadata"]["operator_kinds"] == ["MULTIPLY"]
    assert parser_log["metadata"]["has_equality"] is False
    pieces = [
        piece
        for piece in debug["render_pieces"]
        if piece["owner"] == "basic_arithmetic_expression"
    ]
    assert [piece["provenance"] for piece in pieces] == [
        "GENERATED_READING",
        "GENERATED_READING",
        "GENERATED_READING",
    ]
    assert [piece["source_span"] for piece in pieces] == [
        {"start": 0, "end": 4, "length": 4},
        {"start": 5, "end": 6, "length": 1},
        {"start": 7, "end": 11, "length": 4},
    ]
    validation = trace["validation_logs"][0]
    assert validation["passed"] is True


def test_arithmetic_parser_uses_typed_unary_and_binary_tokens() -> None:
    parsed = parse_basic_arithmetic_expression_at("3 + -4", 0)
    assert parsed is not None
    assert parsed.operand_kinds == ("NUMBER", "SIGNED_NUMBER")
    assert parsed.operator_kinds == ("ADD",)
    assert parsed.has_equality is False


def test_basic_arithmetic_korean_sentence_e2e() -> None:
    text = (
        "계산식은 3+4=7이고, 보정식은 +3.4 x -2.3이며, 분수식은 1/3+2/3이다. "
        "경로 /path/3+4/log와 코드 A+B는 보존한다."
    )
    expected = (
        "계산식은 삼 더하기 사는 칠이고, 보정식은 플러스 삼쩜사 곱하기 마이너스 이쩜삼이며, "
        "분수식은 삼분의 일 더하기 삼분의 이이다. 경로 /path/3+4/log와 코드 A+B는 보존한다."
    )
    assert transform(text) == expected


def _claim_logs(text: str) -> list[dict[str, object]]:
    trace = transform_debug(text)["debug"].get("trace") or {}
    return trace.get("claim_logs", [])
