from __future__ import annotations

from pathlib import Path


def test_phase35b_canonical_policy_file_exists() -> None:
    assert Path("docs/policies/TTS_Preprocessor_policy.md").is_file()


def test_phase35b_canonical_policy_changelog_file_exists() -> None:
    assert Path("docs/policies/TTS_Preprocessor_policy_changelog.md").is_file()
