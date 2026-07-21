from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.main import transform


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "batch1_allowed_output_diffs.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
STABLE_DECISIONS = FIXTURE["stable_decisions"]
ALLOWED_DIFFS = FIXTURE["allowed_diffs"]


def test_batch1_allowed_diff_fixture_is_well_formed():
    assert FIXTURE["batch_id"] == "policy-alignment-batch-1"

    stable_ids = {row["decision_id"] for row in STABLE_DECISIONS}
    diff_ids = {row["decision_id"] for row in ALLOWED_DIFFS}
    assert stable_ids == {
        "standalone-time-zero",
        "standalone-time-day-boundary",
    }
    assert diff_ids == {
        "spaced-hyphen-separator-preservation",
        "spaced-hyphen-korean-tail",
        "spaced-hyphen-phone-shaped",
        "spaced-hyphen-leading-zero-blocks",
        "spaced-hyphen-decimal-blocks",
        "spaced-hyphen-date-shaped",
        "spaced-hyphen-attached-korean-sentence",
        "caret-cubic-meter",
    }
    assert stable_ids.isdisjoint(diff_ids)
    assert len(stable_ids) == len(STABLE_DECISIONS)
    assert len(diff_ids) == len(ALLOWED_DIFFS)

    for row in ALLOWED_DIFFS:
        assert row["status"] in {"pending", "applied"}
        assert row["before"] != row["after"]
        assert row["scope"]


@pytest.mark.parametrize(
    "row",
    STABLE_DECISIONS,
    ids=lambda row: row["decision_id"],
)
def test_batch1_stable_decisions_remain_exact(row: dict):
    assert transform(row["input"]) == row["expected"]


@pytest.mark.parametrize(
    "row",
    ALLOWED_DIFFS,
    ids=lambda row: row["decision_id"],
)
def test_batch1_output_matches_declared_transition_state(row: dict):
    expected = row["before"] if row["status"] == "pending" else row["after"]
    assert transform(row["input"]) == expected
