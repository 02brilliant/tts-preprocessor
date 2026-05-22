from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("12,345,678,901", "백이십삼억 사천오백육십칠만 팔천구백일"),
        (
            "12,345,678,901,234",
            "십이조 삼천사백오십육억 칠천팔백구십만 천이백삼십사",
        ),
        (
            "12,345,678,901,234,567",
            "일경 이천삼백사십오조 육천칠백팔십구억 백이십삼만 사천오백육십칠",
        ),
        ("12,345", "만 이천삼백사십오"),
        ("123,456", "십이만 삼천사백오십육"),
        ("1,234,567", "백이십삼만 사천오백육십칠"),
        ("10,000", "만"),
        ("100,000,000", "일억"),
        ("1,000,000,000", "십억"),
        ("1,000,000,000,000", "일조"),
        ("1,000,000,000,000,000", "천조"),
        ("10,000,000,000,000,000", "일경"),
        ("100,000,001", "일억 일"),
        ("100,010,001", "일억 만 일"),
        ("1,000,100,000", "십억 십만"),
    ],
)
def test_large_number_group_spacing(source: str, expected: str) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("101명", "백일 명"),
        ("12,345명", "만 이천삼백사십오 명"),
        ("123,456명", "십이만 삼천사백오십육 명"),
        (
            "12,345,678,901,234명",
            "십이조 삼천사백오십육억 칠천팔백구십만 천이백삼십사 명",
        ),
        ("12,345원", "만 이천삼백사십오 원"),
        ("12,345,678원", "천이백삼십사만 오천육백칠십팔 원"),
        ("₩12,345,678", "천이백삼십사만 오천육백칠십팔 원"),
        ("2조 3,400억 원", "이조 삼천사백억 원"),
    ],
)
def test_large_number_group_spacing_with_suffixes(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("id_12345", "id_12345"),
        ("log_2025_01_03", "log_2025_01_03"),
        ("https://example.com/12,345", "https://example.com/12,345"),
    ],
)
def test_large_number_spacing_preserve_contexts(
    source: str, expected: str
) -> None:
    assert transform(source) == expected
