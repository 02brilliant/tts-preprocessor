from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.main import transform


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "contextual_number_unit_llm_acceptance.json"
)


def _acceptance_cases() -> list[pytest.ParameterSet]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [
        pytest.param(source, expected, id=f"{group['group']}-{index:02d}")
        for group in payload
        for index, (source, expected) in enumerate(group["cases"], start=1)
    ]


@pytest.mark.parametrize(("source", "expected"), _acceptance_cases())
def test_contextual_number_unit_acceptance(
    source: str,
    expected: str,
) -> None:
    assert transform(source) == expected
