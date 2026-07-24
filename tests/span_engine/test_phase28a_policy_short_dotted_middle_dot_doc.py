from pathlib import Path

def test_phase28a_policy_document_content():
    """
    Phase 28A/29F: canonical policy short dotted / middle-dot numeric 문서 내용 검증.
    """
    policy_path = Path("docs/TTS_Preprocessor_policy.md")
    assert policy_path.exists(), f"{policy_path} 파일이 존재하지 않습니다."

    content = policy_path.read_text(encoding="utf-8")

    required_phrases = [
        "fixed event / event keyword",
        "middle_dot_numeric_block",
        "12.3 비상계엄 -> 십이삼 비상계엄",
        "12·3 비상계엄 -> 십이삼 비상계엄",
        "12.3-비상계엄 -> 십이삼-비상계엄",
        "12·3 -> 십이 삼",
        "12·3수치 -> 십이 삼수치",
        "12 . 3 -> 12 . 3",
        "12 · 3 -> 십이 · 삼",
        "[12.3] -> 12.3",
    ]
    for phrase in required_phrases:
        assert phrase in content, f"정책 문서에 '{phrase}' 문구가 포함되어 있지 않습니다."
