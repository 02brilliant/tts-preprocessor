from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1차 시험", "일-차 시험"),
        ("1위", "일-위"),
        ("1위가", "일-위가"),
        ("3차원", "삼-차원"),
        ("1차량", "일-차량"),
        ("2차로", "이-차로"),
        ("1위권", "일-위권"),
        ("1위자", "일-위자"),
        ("1차례", "한-차례"),
        ("1차원의", "일-차원의"),
        ("1~3위", "일에서 삼-위"),
        ("1~3째", "첫째에서 셋째"),
    ],
)
def test_sino_cha_wi_and_existing_counter_range_contracts(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["01차원", "A1차원", "1차원abc", "1차원론", "1위권자"],
)
def test_cha_wi_partial_number_read_is_blocked(text: str) -> None:
    assert transform(text) == text


def test_fixed_cha_compound_claim_excludes_following_particle() -> None:
    output = transform_with_trace("1차원의")

    assert output.normalized_text == "일-차원의"
    assert [(log.owner, log.span.start, log.span.end) for log in output.trace.claim_logs] == [
        ("contextual_number_unit", 0, 3)
    ]
    assert output.render_pieces[-1].text == "의"
    assert output.render_pieces[-1].provenance == "ORIGINAL_KOREAN"


def test_deung_and_ho_existing_contextual_contracts_are_unchanged() -> None:
    assert transform("1등") == "1등"
    assert transform("1호") == "1호"
