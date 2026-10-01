"""Drift guard: docs/TTS_Preprocessor_numeric_matrix.md vs engine.main.transform.

Canonical backtick table rows outside historical §11 must match production
output.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from engine.main import transform


NUMERIC_MATRIX = Path("docs/TTS_Preprocessor_numeric_matrix.md")
ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|")


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


def _current_policy_examples() -> list[tuple[str, str, str]]:
    """Check explicitly current sections; never rewrite historical expectations."""
    sections = (
        ("docs/TTS_Preprocessor_policy.md", "숫자 발화 경계 canonical 정책"),
        ("docs/TTS_Preprocessor_level_policy.md", "규칙 엔진 숫자 발화 경계"),
        ("docs/TTS_Preprocessor_level_policy.md", "숫자 장음 상시 출력 (2026-10-01)"),
    )
    examples = []
    for path, title in sections:
        document = Path(path).read_text(encoding="utf-8")
        section = document.split("## " + title + "\n", 1)[1].split("\n## ", 1)[0]
        pairs = []
        for block in re.findall(r"```text\n(.*?)\n```", section, re.DOTALL):
            for line in block.splitlines():
                source, expected = line.split(" -> ", 1)
                pairs.append((source, expected))
        pairs.extend(re.findall(r"`([^`]+?)→([^`]+)`", section))
        for sources, expected in pairs:
            aliases = [sources]
            if "/" in sources:
                left, right = sources.split("/", 1)
                # Only equivalent attached/spaced aliases, never km/L or a fraction.
                if left.replace(" ", "") == right.replace(" ", ""):
                    aliases = [left, right]
            for source in aliases:
                examples.append((path, source.strip(), expected.strip()))
    return examples


_CURRENT_POLICY_EXAMPLES = _current_policy_examples()


def test_current_policy_example_coverage():
    assert len(_CURRENT_POLICY_EXAMPLES) >= 30
    assert any(source == "2025년" and expected == "이~천이십오년"
               for _, source, expected in _CURRENT_POLICY_EXAMPLES)


@pytest.mark.parametrize("path,source,expected", _CURRENT_POLICY_EXAMPLES)
def test_current_policy_examples_match_implementation(path, source, expected):
    del path
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("section", "surface", "doc_expected"),
    _CANONICAL_ROWS,
    ids=[f"{surface}" for _section, surface, _expected in _CANONICAL_ROWS],
)
def test_numeric_matrix_canonical_rows_match_engine(
    section: str, surface: str, doc_expected: str
) -> None:
    del section
    assert transform(surface) == doc_expected
