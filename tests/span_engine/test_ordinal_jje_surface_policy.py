from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.ordinal_jje import ordinal_jje_reading
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1째", "첫째"),
        ("2째", "둘째"),
        ("12째", "열두째"),
        ("21째", "스물한째"),
        ("40째", "사십째"),
        ("7째만", "일곱째만"),
        ("7째abc", "일곱째abc"),
        ("제12째", "제-열두째"),
        ("제 12째", "제-열두째"),
        ("2번째와 3째", "두-번째와 셋째"),
    ],
)
def test_ordinal_jje_canonical_readings(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["0째", "01째", "2.5째", "A제12째"],
)
def test_invalid_or_deferred_ordinal_jje_preserves(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("raw_number", "expected"),
    [('1', '첫째'), ('2', '둘째'), ('12', '열두째'), ('40', '사십째')],
)
def test_ordinal_jje_reading_policy(raw_number: str, expected: str) -> None:
    assert ordinal_jje_reading(raw_number) == expected


def test_ordinal_jje_claims_only_number_and_jje() -> None:
    output = transform_with_trace("7째만")
    assert output.normalized_text == "일곱째만"
    assert [(log.owner, log.span.start, log.span.end) for log in output.trace.claim_logs] == [
        ("ordinal_jje", 0, 2)
    ]
