from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.main import transform


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "batch6_allowed_output_diffs.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
STABLE_DECISIONS = FIXTURE["stable_decisions"]
ALLOWED_DIFFS = FIXTURE["allowed_diffs"]


def test_batch6_fixture_is_well_formed() -> None:
    assert FIXTURE["batch_id"] == "policy-alignment-batch-6"
    decision_ids = {row["decision_id"] for row in STABLE_DECISIONS}
    assert decision_ids == {
        "leading-one-100000000000000000000",
        "mixed-sentence-forum-ordinal-and-yeo",
        "mixed-sentence-large-yeo",
        "mixed-sentence-ordinal-and-acronym-tail",
        "scaling-large-comma-decimal",
        "scenario-emergency-and-general-number-same-sentence",
    }
    assert len(decision_ids) == len(STABLE_DECISIONS) == 6
    assert ALLOWED_DIFFS == []
    assert all(row["owner_contract"] for row in STABLE_DECISIONS)


@pytest.mark.parametrize(
    "row", STABLE_DECISIONS, ids=lambda row: row["decision_id"]
)
def test_batch6_stable_decisions_remain_exact(row: dict[str, str]) -> None:
    assert transform(row["input"]) == row["expected"]


def test_batch6_does_not_declare_runtime_output_transitions() -> None:
    assert ALLOWED_DIFFS == []
