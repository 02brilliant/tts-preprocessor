from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.main import transform


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "batch2_allowed_output_diffs.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
STABLE_DECISIONS = FIXTURE["stable_decisions"]
ALLOWED_DIFFS = FIXTURE["allowed_diffs"]


def test_batch2_fixture_is_well_formed() -> None:
    assert FIXTURE["batch_id"] == "policy-alignment-batch-2"
    decision_ids = {row["decision_id"] for row in STABLE_DECISIONS}
    assert decision_ids == {
        "digit-mode-leading-zero-003",
        "digit-mode-leading-zero-007",
        "digit-mode-leading-zero-01",
        "interaction-identifier-digit-mode-plus-date",
        "interaction-leading-zero-bare-date-unit-counter",
        "interaction-leading-zero-bare-time-override",
        "interaction-phone-digit-mode-plus-counter-override",
        "mixed-identifier-leading-zero-digit-mode",
        "override-currency-beats-leading-zero",
        "override-time-hour-minute-beats-leading-zero",
        "override-unit-beats-leading-zero",
        "regression-leading-zero-counter-override",
        "regression-leading-zero-digit-mode",
        "regression-leading-zero-time-override",
    }
    assert len(decision_ids) == len(STABLE_DECISIONS) == 14
    assert ALLOWED_DIFFS == []
    assert all(row["owner_contract"] for row in STABLE_DECISIONS)


@pytest.mark.parametrize(
    "row",
    STABLE_DECISIONS,
    ids=lambda row: row["decision_id"],
)
def test_batch2_stable_decisions_remain_exact(row: dict[str, str]) -> None:
    assert transform(row["input"]) == row["expected"]


def test_batch2_does_not_declare_runtime_output_transitions() -> None:
    assert ALLOWED_DIFFS == []
