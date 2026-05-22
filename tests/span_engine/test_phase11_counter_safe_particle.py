from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("21명을 봤다", "스물한 명을 봤다"),
        ("21명를 봤다", "스물한 명를 봤다"),
        ("21명은 왔다", "스물한 명은 왔다"),
        ("21명는 왔다", "스물한 명는 왔다"),
        ("3개으로 처리", "세 개으로 처리"),
    ],
)
def test_counter_does_not_trigger_broad_particle_correction(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("21명를 봤다", "스물한 명을 봤다"),
        ("21명는 왔다", "스물한 명은 왔다"),
        ("3개으로 처리", "세 개로 처리"),
    ],
)
def test_counter_particle_forbidden_signatures_do_not_appear(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden
