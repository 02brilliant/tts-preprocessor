from __future__ import annotations

import json
from pathlib import Path

import pytest

from LLM.standard_pronunciation import (
    StandardPronunciationDataError,
    entries_for_mode,
    load_stage5_pronunciations,
)


def test_packaged_stage5_registry_separates_deterministic_and_contextual() -> None:
    deterministic = entries_for_mode("deterministic")
    contextual = entries_for_mode("contextual")

    assert len(deterministic) >= 20
    assert {entry.surface for entry in deterministic} >= {
        "인기",
        "국물",
        "같이",
        "학교",
        "색년필",
    }
    assert [(entry.surface, entry.pronunciation) for entry in contextual] == [
        ("대가", "대까")
    ]
    assert all(entry.source.startswith("https://") for entry in deterministic + contextual)


def test_stage5_registry_rejects_duplicate_mode_surface(tmp_path: Path) -> None:
    path = tmp_path / "stage5.json"
    entry = {
        "surface": "국물",
        "pronunciation": "궁물",
        "mode": "deterministic",
        "category": "nasal_assimilation",
        "sense_hint": "독립 어휘",
        "source": "https://example.invalid",
    }
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [entry, entry]}),
        encoding="utf-8",
    )

    with pytest.raises(StandardPronunciationDataError, match="중복 표면"):
        load_stage5_pronunciations(path)


@pytest.mark.parametrize("mode", ("", "automatic", True))
def test_stage5_registry_rejects_invalid_mode(tmp_path: Path, mode) -> None:
    path = tmp_path / f"stage5-{mode!s}.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "surface": "국물",
                        "pronunciation": "궁물",
                        "mode": mode,
                        "category": "nasal_assimilation",
                        "sense_hint": "독립 어휘",
                        "source": "https://example.invalid",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(StandardPronunciationDataError):
        load_stage5_pronunciations(path)
