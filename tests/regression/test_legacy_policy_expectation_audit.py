from __future__ import annotations

import json
from pathlib import Path

from engine.main import transform


AUDIT_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "legacy_policy_expectation_audit.json"
)
AUDIT_ROWS = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_legacy_policy_audit_empty_state_is_well_formed() -> None:
    assert AUDIT_ROWS == []
    assert AUDIT_PATH.read_text(encoding="utf-8") == "[]\n"
    keys = [(row["input"], row["policy_expected"]) for row in AUDIT_ROWS]
    assert len(keys) == len(set(keys)) == 0
    assert [row["disposition"] for row in AUDIT_ROWS] == []
    assert {row["disposition"] for row in AUDIT_ROWS} == set()


def test_audited_span_outputs_remain_byte_exact() -> None:
    for row in AUDIT_ROWS:
        assert row["policy_expected"] != row["span_expected"]
        assert transform(row["input"]) == row["span_expected"]
