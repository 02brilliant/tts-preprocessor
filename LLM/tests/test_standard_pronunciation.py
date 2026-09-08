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
        "색연필",
        "읽습니다",
        "밟는",
        "꽃다발",
        "값이",
    }
    assert [(entry.surface, entry.pronunciation) for entry in contextual] == [
        ("대가", "대까")
    ]
    assert all(entry.source.startswith("https://") for entry in deterministic + contextual)
    assert len({entry.surface for entry in deterministic}) == len(deterministic)
    assert {entry.paradigm_id for entry in deterministic} >= {
        "읽다",
        "밟다",
        "넓다",
        "읊다",
        "않다",
    }
    assert {entry.boundary_type for entry in deterministic + contextual} <= {
        "contextual",
        "fixed_phrase",
        "noun",
        "predicate_complete",
        "predicate_form",
    }


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


def _write_registry(tmp_path: Path, entry: dict) -> Path:
    path = tmp_path / "stage5-invalid.json"
    path.write_text(
        json.dumps({"schema_version": 2, "entries": [entry]}),
        encoding="utf-8",
    )
    return path


def _valid_entry(**overrides) -> dict:
    entry = {
        "surface": "읽고",
        "pronunciation": "일꼬",
        "mode": "deterministic",
        "category": "consonant_cluster",
        "sense_hint": "동사 활용형",
        "source": "https://example.invalid",
        "boundary_type": "predicate_form",
        "allowed_tails": ["도"],
        "paradigm_id": "읽다",
    }
    entry.update(overrides)
    return entry


@pytest.mark.parametrize(
    "overrides",
    (
        {"category": "general_g2p"},
        {"source": "http://example.invalid"},
        {"surface": "읽고!"},
        {"boundary_type": "prefix"},
        {"allowed_tails": ["도", "도"]},
        {"allowed_tails": ["-도"]},
        {"paradigm_id": ""},
    ),
)
def test_stage5_registry_rejects_invalid_schema2_metadata(
    tmp_path: Path,
    overrides: dict,
) -> None:
    path = _write_registry(tmp_path, _valid_entry(**overrides))
    with pytest.raises(StandardPronunciationDataError):
        load_stage5_pronunciations(path)


def test_stage5_registry_rejects_cross_mode_duplicate_surface(tmp_path: Path) -> None:
    deterministic = _valid_entry()
    contextual = _valid_entry(
        mode="contextual",
        category="contextual_standard_pronunciation",
        boundary_type="contextual",
    )
    path = tmp_path / "stage5-duplicate.json"
    path.write_text(
        json.dumps({"schema_version": 2, "entries": [deterministic, contextual]}),
        encoding="utf-8",
    )
    with pytest.raises(StandardPronunciationDataError, match="중복 표면"):
        load_stage5_pronunciations(path)


def test_stage5_registry_rejects_pronunciation_chain(tmp_path: Path) -> None:
    first = _valid_entry(surface="읽고", pronunciation="일꼬")
    second = _valid_entry(surface="일꼬", pronunciation="일꼬요")
    path = tmp_path / "stage5-chain.json"
    path.write_text(
        json.dumps({"schema_version": 2, "entries": [first, second]}),
        encoding="utf-8",
    )
    with pytest.raises(StandardPronunciationDataError, match="연쇄 변환"):
        load_stage5_pronunciations(path)
