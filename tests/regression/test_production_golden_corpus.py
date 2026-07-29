from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from engine.api_interface import normalize_text
from engine.main import transform


GOLDEN_CORPUS_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "production_golden.jsonl"
)


def load_golden_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        GOLDEN_CORPUS_PATH.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        case = json.loads(line)
        assert set(case) == {"id", "input", "expected", "tags"}, line_number
        assert all(isinstance(case[key], str) for key in ("id", "input", "expected"))
        assert isinstance(case["tags"], list)
        assert all(isinstance(tag, str) for tag in case["tags"])
        cases.append(case)

    assert cases
    assert len({case["id"] for case in cases}) == len(cases)
    return cases


GOLDEN_CASES = load_golden_cases()


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda case: case["id"])
def test_canonical_span_golden_corpus(case: dict[str, Any]) -> None:
    assert transform(case["input"]) == case["expected"]


def test_public_source_entrypoints_share_canonical_output() -> None:
    case = next(case for case in GOLDEN_CASES if case["id"] == "simple-and-compound-unit")
    source = case["input"]
    expected = case["expected"]

    assert tuple(inspect.signature(transform).parameters) == ("text",)
    assert normalize_text(source) == expected
