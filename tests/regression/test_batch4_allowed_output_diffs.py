from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.main import transform


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "batch4_allowed_output_diffs.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
STABLE_DECISIONS = FIXTURE["stable_decisions"]
ALLOWED_DIFFS = FIXTURE["allowed_diffs"]


def test_batch4_fixture_is_well_formed() -> None:
    assert FIXTURE["batch_id"] == "policy-alignment-batch-4"
    stable_ids = {row["decision_id"] for row in STABLE_DECISIONS}
    diff_ids = {row["decision_id"] for row in ALLOWED_DIFFS}
    assert stable_ids == {
        "interaction-middle-dot-and-leading-zero-blocks",
        "interaction-middle-dot-time-tail-guard",
        "interaction-middle-dot-unit-tail-guard",
        "middle-dot-leading-zero-first-block",
        "middle-dot-leading-zero-second-block",
        "preserve-one-digit-right-dotted-event",
        "scenario-event-plus-ambiguous-decimal",
    }
    assert diff_ids == {"adversarial-spaced-middle-dot-right"}
    assert stable_ids.isdisjoint(diff_ids)
    assert len(STABLE_DECISIONS) == 7
    assert len(ALLOWED_DIFFS) == 1
    assert all(row["owner_contract"] for row in STABLE_DECISIONS)
    for row in ALLOWED_DIFFS:
        assert row["status"] in {"pending", "applied"}
        assert row["before"] != row["after"]
        assert row["scope"]


@pytest.mark.parametrize(
    "row", STABLE_DECISIONS, ids=lambda row: row["decision_id"]
)
def test_batch4_stable_decisions_remain_exact(row: dict[str, str]) -> None:
    assert transform(row["input"]) == row["expected"]


@pytest.mark.parametrize(
    "row", ALLOWED_DIFFS, ids=lambda row: row["decision_id"]
)
def test_batch4_output_matches_declared_transition_state(
    row: dict[str, str]
) -> None:
    expected = row["before"] if row["status"] == "pending" else row["after"]
    assert transform(row["input"]) == expected
