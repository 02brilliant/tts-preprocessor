from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "A3가",
        "3가abc",
        "3가kg",
        "3-가",
        "3 가",
        "03가",
        "3.5가",
        "1,000가",
        "[종로3가]",
        "(종로3가)",
    ],
)
def test_phase17c_admin_suffix_preserve_or_protected_cases(text: str) -> None:
    if text.startswith("(") and text.endswith(")"):
        assert transform(text) == ""
    elif text.startswith("[") and text.endswith("]"):
        assert transform(text) == text[1:-1]
    else:
        assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-3가", "마이너스 삼가"),
        ("+3가", "플러스 삼가"),
    ],
)
def test_phase16d_signed_number_updates_former_admin_suffix_preserve(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3가 맞다", "삼가 맞다"),
        ("12로 나누다", "십이로 나누다"),
        ("21호", "이십일 호"),
        ("101동", "백일 동"),
    ],
)
def test_phase17c_admin_suffix_conflict_cases_keep_existing_owner_behavior(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
