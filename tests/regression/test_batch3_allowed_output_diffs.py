from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.main import transform


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "batch3_allowed_output_diffs.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
STABLE_DECISIONS = FIXTURE["stable_decisions"]
ALLOWED_DIFFS = FIXTURE["allowed_diffs"]


def test_batch3_fixture_is_well_formed() -> None:
    assert FIXTURE["batch_id"] == "policy-alignment-batch-3"
    decision_ids = {row["decision_id"] for row in STABLE_DECISIONS}
    assert decision_ids == {
        "adversarial-ratio-like-colon-form",
        "independent-time-with-afternoon-marker",
        "independent-time-with-josa-binding",
        "regression-independent-time-afternoon",
        "scenario-event-time-range",
        "hhmm-zero-minute-omission",
        "hhmm-24-01-strong-time",
        "colon-one-digit-minute-semantic-pair",
        "colon-score-context",
        "colon-ratio-context",
        "hhmm-24-00-zero-minute-omission",
        "hhmmss-standalone-13-preserve",
        "hhmmss-standalone-3-preserve",
        "hhmmss-sentence-13-preserve",
        "hhmmss-sentence-3-preserve",
        "suffix-clock-phonetic-spacing",
    }
    assert len(decision_ids) == len(STABLE_DECISIONS) == 16
    assert ALLOWED_DIFFS == []
    assert all(row["owner_contract"] for row in STABLE_DECISIONS)


@pytest.mark.parametrize(
    "row",
    STABLE_DECISIONS,
    ids=lambda row: row["decision_id"],
)
def test_batch3_stable_decisions_remain_exact(row: dict[str, str]) -> None:
    assert transform(row["input"]) == row["expected"]


def test_batch3_does_not_declare_runtime_output_transitions() -> None:
    assert ALLOWED_DIFFS == []
