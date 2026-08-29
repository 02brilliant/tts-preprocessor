from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("1번째", "첫-번째"),
        ("제7번째", "제-일곱-번째"),
        ("1~3번째", "첫-번째에서 세-번째"),
        ("3명", "세-명"),
        ("3 명", "세-명"),
        ("1차례", "한-차례"),
        ("3시간", "세-시간"),
        ("3시", "세-시"),
        ("5kg", "오-킬로그램"),
        ("5 kg", "오-킬로그램"),
        ("10bp", "십-베이시스 포인트"),
        ("20%", "이십-퍼센트"),
        ("₩1,234.50", "천이백삼십사쩜오영-원"),
        ("3만kg", "삼만-킬로그램"),
        ("5번길", "오-번길"),
        ("1차원", "일-차원"),
        ("1위", "일-위"),
        ("제1회", "제-일회"),
        ("제3 조", "제-삼 조"),
        ("제10kg", "제십-킬로그램"),
        ("제1", "제-일"),
    ),
)
def test_confirmed_numeric_spoken_boundaries_use_ascii_hyphen(
    source: str,
    expected: str,
) -> None:
    actual = transform(source)

    assert actual == expected
    assert "\N{EN DASH}" not in actual
    assert "\N{EM DASH}" not in actual
    assert " -" not in actual
    assert "- " not in actual
    assert transform(actual) == actual


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("1째", "첫째"),
        ("제12째", "제-열두째"),
        ("2025년", "이천이십오년"),
        ("25℃", "이십오도"),
        ("1분기", "일분기"),
        ("5분15초", "오분 십오초"),
    ),
)
def test_attached_or_structural_exceptions_keep_their_registered_shape(
    source: str,
    expected: str,
) -> None:
    assert transform(source) == expected


def test_generated_boundary_is_part_of_locked_generated_reading() -> None:
    ordinal = transform_with_trace("1번째")
    unit = transform_with_trace("5kg")

    assert ordinal.normalized_text == "첫-번째"
    assert ordinal.render_pieces[0].text == "첫-"
    assert ordinal.render_pieces[0].provenance == "GENERATED_READING"
    assert unit.normalized_text == "오-킬로그램"
    assert unit.render_pieces[0].text == "오-킬로그램"
    assert unit.render_pieces[0].provenance == "GENERATED_READING"
