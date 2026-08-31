"""Drift guard: docs/TTS_Preprocessor_numeric_matrix.md vs engine.main.transform.

Canonical backtick table rows outside historical §11 must match production
output, except for an explicit quarantine of known stale doc expecteds. When
the doc or engine changes for a quarantined surface, update or remove the
quarantine entry in the same change.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from engine.main import transform


NUMERIC_MATRIX = Path("docs/TTS_Preprocessor_numeric_matrix.md")
ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|")

# surface -> (doc_expected, engine_actual). Doc prose is stale relative to the
# hyphen / middle-dot / preserve contracts already enforced by tests.
KNOWN_DOC_ENGINE_DRIFT: dict[str, tuple[str, str]] = {
    "3..140": ("삼..백사십", "3..140"),
    "–2.03%": ("마이너스 이쩜영삼 퍼센트", "마이너스 이쩜영삼-퍼센트"),
    "1–2kg": ("일에서 이 킬로그램", "일에서 이-킬로그램"),
    "국토위성 1·2호기": ("국토위성 일 이호기", "국토위성 일·이호기"),
    "3·4호기를 도입한다": ("삼 사호기를 도입한다", "삼·사호기를 도입한다"),
}


def _matrix_rows() -> list[tuple[str, str, str]]:
    section = ""
    rows: list[tuple[str, str, str]] = []
    for line in NUMERIC_MATRIX.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        match = ROW_RE.match(line)
        if match is None:
            continue
        rows.append((section, match.group(1), match.group(2)))
    return rows


def _canonical_rows() -> list[tuple[str, str, str]]:
    """Exclude historical §11 analysis inventory (explicitly non-canonical)."""

    return [
        row
        for row in _matrix_rows()
        if not row[0].startswith("11.")
    ]


def test_numeric_matrix_document_exists_and_names_official_path() -> None:
    text = NUMERIC_MATRIX.read_text(encoding="utf-8")
    assert NUMERIC_MATRIX.is_file()
    assert "engine.main.transform(text)" in text
    assert "## 10. Open follow-up decisions" in text
    assert "Historical, Non-Canonical" in text


def test_numeric_matrix_has_canonical_backtick_rows() -> None:
    rows = _canonical_rows()
    # Current backtick current-output rows live mainly in §3/§4/§14; §11 is
    # excluded as historical non-canonical inventory.
    assert len(rows) >= 50
    surfaces = [surface for _, surface, _ in rows]
    assert "1" in surfaces
    assert "국토위성 1·2호기" in surfaces


_CANONICAL_ROWS = _canonical_rows()


@pytest.mark.parametrize(
    ("section", "surface", "doc_expected"),
    _CANONICAL_ROWS,
    ids=[f"{surface}" for _section, surface, _expected in _CANONICAL_ROWS],
)
def test_numeric_matrix_canonical_rows_match_engine_or_quarantine(
    section: str, surface: str, doc_expected: str
) -> None:
    del section
    actual = transform(surface)
    if surface in KNOWN_DOC_ENGINE_DRIFT:
        stale_doc, engine_expected = KNOWN_DOC_ENGINE_DRIFT[surface]
        assert doc_expected == stale_doc, (
            f"{surface!r} quarantine doc expected changed; update "
            "KNOWN_DOC_ENGINE_DRIFT or fix the matrix row"
        )
        assert actual == engine_expected, (
            f"{surface!r} quarantine engine output changed; update "
            "KNOWN_DOC_ENGINE_DRIFT or resolve the matrix row"
        )
        return
    assert actual == doc_expected


def test_known_doc_engine_drift_quarantine_is_exhaustive_for_canonical_rows() -> None:
    unexpected: list[str] = []
    for _section, surface, doc_expected in _canonical_rows():
        actual = transform(surface)
        if actual == doc_expected:
            continue
        if surface not in KNOWN_DOC_ENGINE_DRIFT:
            unexpected.append(f"{surface!r}: doc={doc_expected!r} engine={actual!r}")
    assert not unexpected, (
        "New numeric_matrix canonical drifts found; add quarantine entries or "
        f"fix the doc:\n" + "\n".join(unexpected)
    )


def test_known_doc_engine_drift_quarantine_has_no_stale_entries() -> None:
    canonical_surfaces = {surface for _, surface, _ in _canonical_rows()}
    for surface in KNOWN_DOC_ENGINE_DRIFT:
        assert surface in canonical_surfaces, (
            f"quarantine entry {surface!r} is missing from canonical matrix rows"
        )
        stale_doc, engine_expected = KNOWN_DOC_ENGINE_DRIFT[surface]
        # Quarantine is only for real mismatches; aligned rows must be removed.
        assert stale_doc != engine_expected
