from __future__ import annotations

from pathlib import Path


def test_phase28g_policy_document_contains_decision_notes() -> None:
    """Canonical policy doc must contain Phase 28G binding decisions."""
    text = Path("docs/TTS_Preprocessor_policy.md").read_text(encoding="utf-8")

    required_phrases = [
        "middle-dot numeric block fallback",
        "회의는 13:05(시작)에 열린다 -> 회의는 십삼시 오분에 열린다",
        "13:05 -> 13:05",
        "5·18 -> 오·일팔",
        "5·18 민주화운동 -> 오일팔 민주화운동",
        "bare 5·18 -> 오·일팔",
        "3.5만 -> 삼-쩜-오 만",
        "3.5만 원 -> 삼-쩜-오 만 원",
        "semantic expansion `3.5만 -> 삼만 오천`은 여전히 범위 밖",
    ]
    for phrase in required_phrases:
        assert phrase in text
