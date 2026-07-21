from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.main import transform


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "batch8_allowed_output_diffs.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
STABLE_DECISIONS = FIXTURE["stable_decisions"]
ALLOWED_DIFFS = FIXTURE["allowed_diffs"]


def test_batch8_fixture_is_well_formed() -> None:
    assert FIXTURE["batch_id"] == "policy-alignment-batch-8"
    decision_ids = {row["decision_id"] for row in STABLE_DECISIONS}
    assert decision_ids == {
        "adversarial-protected-two-block-hyphen",
        "typed-surface-e2e-acronym-large-unit-range",
        "typed-surface-e2e-lexical-non-rewrite-hyphen",
        "typed-surface-partial-ai-middle-dot-sentence",
        "typed-surface-partial-hyphen-sequence",
        "typed-surface-partial-unicode-tilde-month",
    }
    assert len(decision_ids) == len(STABLE_DECISIONS) == 6
    assert ALLOWED_DIFFS == []
    assert all(row["owner_contract"] for row in STABLE_DECISIONS)


@pytest.mark.parametrize(
    "row", STABLE_DECISIONS, ids=lambda row: row["decision_id"]
)
def test_batch8_stable_decisions_remain_exact(row: dict[str, str]) -> None:
    assert transform(row["input"]) == row["expected"]


def test_batch8_does_not_declare_runtime_output_transitions() -> None:
    assert ALLOWED_DIFFS == []
