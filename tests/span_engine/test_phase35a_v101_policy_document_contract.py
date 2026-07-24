from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = ROOT / "docs"


def test_phase35a_canonical_policy_document_contract() -> None:
    canonical_path = POLICY_DIR / "TTS_Preprocessor_policy.md"
    changelog_path = POLICY_DIR / "TTS_Preprocessor_policy_changelog.md"

    assert canonical_path.exists()
    assert changelog_path.exists()

    canonical = canonical_path.read_text(encoding="utf-8")
    changelog = changelog_path.read_text(encoding="utf-8")

    for phrase in [
        "현재 TTS Preprocessor 구현과 테스트 판단의 단일 canonical policy",
        "Absolute Preserve",
        "Owner Fallback Candidate",
        "Terminal Fallback Preserve",
        "Korean Eligibility Gate",
        "Global Korean Eligibility Bypass",
        "standalone supported token",
        "numeric-list line",
        "Code-like / URL / email / file path / JSON / shell command preserve",
        "사용자-visible 대괄호 삽입 금지",
        "owner-local alias symbol",
        "전역 Unicode normalization",
        "if no_hangul(text)",
    ]:
        assert phrase in canonical

    assert "릴리스 로그가 아니라 현재 canonical policy로 정리된 주요 정책 변경과 결정 기록" in changelog
    assert "docs/TTS_Preprocessor_policy.md" in changelog
    assert "결정 기록으로만 사용" in changelog
