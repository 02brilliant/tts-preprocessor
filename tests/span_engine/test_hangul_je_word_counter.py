from __future__ import annotations

import pytest

from engine.span_engine.transform import transform


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "이제 10년밖에 되지 않았지만, 10년밖에 되지 않았다.",
            "이제 십년밖에 되지 않았지만, 십년밖에 되지 않았다.",
        ),
        ("이제 10년밖에", "이제 십년밖에"),
        ("이제 10년", "이제 십년"),
        ("어제 10년", "어제 십년"),
        ("경제 10년", "경제 십년"),
        ("지금 10년", "지금 십년"),
        ("이제 10개", "이제 열 개"),
        ("과제 10개", "과제 열 개"),
        ("이제 10명", "이제 열 명"),
        ("이제 10", "이제 십"),
        ("제 10년", "제 십년"),
        ("제10년", "제 십년"),
    ],
)
def test_hangul_word_ending_in_je_does_not_block_following_counter(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("A제 5차", "A제 오차"),
        ("A제 10년", "A제 십년"),
        ("A제 2문항", "A제 두 문항"),
    ],
)
def test_latin_glued_je_does_not_apply_ordinal_rule_to_following_number(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize("source", ["A제5차", "A제10년", "A제2문항"])
def test_latin_glued_attached_je_number_still_preserves(source: str) -> None:
    assert transform(source) == source
