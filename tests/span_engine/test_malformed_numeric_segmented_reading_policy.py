from __future__ import annotations

import pytest

from engine.main import transform


def prod(text: str) -> str:
    return transform(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("25..50", "25..50"),
        ("3..140", "3..140"),
        ("2,34", "2,34"),
        ("2,,345", "2,,345"),
        ("2,34억", "2,34억"),
        ("2,,345억", "2,,345억"),
        ("3백..4십만", "3백..4십만"),
        ("2천8백.28억", "2천8백.28억"),
        ("2천8백..28억", "2천8백..28억"),
        ("2천8백28..5억", "2천8백28..5억"),
    ],
)
def test_malformed_numeric_current_behavior_audit(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+.5", "+.5"),
        ("-.5", "-.5"),
        ("+.5억", "+.5억"),
        ("1.", "일."),
        ("1.억", "1.억"),
        ("01.5", "01.5"),
        ("+01.5", "+01.5"),
        ("01.5억", "01.5억"),
        ("+01.5억", "+01.5억"),
        ("1,00.5", "1,00.5"),
        ("+1,00.5원", "+1,00.5원"),
    ],
)
def test_severe_invalid_preserve_audit(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("`25..50억`", "`25..50억`"),
        ('{"value":"25..50억"}', '{"value":"25..50억"}'),
        ("/path/25..50억/log", "/path/25..50억/log"),
        ("https://example.com?q=25..50억", "https://example.com?q=25..50억"),
        ("file-25..50.txt", "file-25..50.txt"),
        ('version-1.5', '버전-일-쩜-오'),
        ("v25..50", "v25..50"),
        ("SKU25..50", "SKU25..50"),
    ],
)
def test_protected_and_code_like_exclusion_current_audit(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3:15", "3:15"),
        ("10:20", "10:20"),
        ("+1:02", "+1:02"),
        ("09:30", "아홉시 삼십분"),
        ("13:05", "십삼시 오분"),
        ("24:09", "이십사시 구분"),
        ("1:02:03", "1:02:03"),
        ("3:4", "삼 대 사"),
        ("25:30", "이십오 대 삼십"),
        ("1:2:3", "일 대 이 대 삼"),
    ],
)
def test_structural_delimiter_colon_like_audit(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1-2", "1-2"),
        ("03-04", "공삼 공사"),
        ("12-31", "12-31"),
        ("123-456", "123-456"),
        ("file-2025-01.txt", "file-2025-01.txt"),
            ('version-1.5', '버전-일-쩜-오'),
        ("+1.5-2kg", "+1.5-2kg"),
        ("-1.5-2kg", "-1.5-2kg"),
        ("1-2kg", "일에서 이-킬로그램"),
        ("1-2개", "일에서 이-개"),
        ("1-2원", "일에서 이-원"),
    ],
)
def test_structural_delimiter_hyphen_dash_like_audit(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1/3", "삼분의 일"),
        ("2026/06/17", "이천이십육년 유월 십칠일"),
        ('15.2km/L', '리터당 십오쩜이 킬로미터'),
        ("/path/1/2/log", "/path/1/2/log"),
    ],
)
def test_structural_delimiter_slash_like_audit(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('25.50', '이십오-쩜-오영'),
        ("12.3 비상계엄", "십이삼 비상계엄"),
        ("v1.2.3", "v1.2.3"),
        ("file.txt", "file.txt"),
        ('pH 7.4', '피에이치 칠-쩜-사'),
    ],
)
def test_structural_delimiter_dot_like_audit(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,000", "천"),
        ('1,000.50', '천-쩜-오영'),
        ("1,00", "1,00"),
        ("2,34", "2,34"),
        ("2,,345", "2,,345"),
    ],
)
def test_structural_delimiter_comma_like_audit(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12·3", "일이·삼"),
        ("12·3 비상계엄", "십이삼 비상계엄"),
        ("1·2·3", "일·이·삼"),
    ],
)
def test_structural_delimiter_middle_dot_like_audit(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1~2", "일에서 이"),
        ("1~2kg", "일에서 이-킬로그램"),
        ('+1.5~2', '플러스 일-쩜-오에서 이'),
        ("1~~2", "1~~2"),
    ],
)
def test_structural_delimiter_tilde_like_audit(text: str, expected: str) -> None:
    assert prod(text) == expected
