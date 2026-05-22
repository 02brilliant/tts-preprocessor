from __future__ import annotations

from engine.span_engine.tokenizer import tokenize_immutable_spans


def _token_summary(text: str) -> list[tuple[str, str, bool]]:
    return [(token.kind, token.raw, token.immutable) for token in tokenize_immutable_spans(text)]


def test_korean_literal_tokenizes_contiguous_modern_hangul_syllables() -> None:
    assert _token_summary("안녕하세요") == [("KOREAN_LITERAL", "안녕하세요", True)]


def test_korean_literals_split_from_plain_ascii_and_digits() -> None:
    assert _token_summary("AI는") == [
        ("PLAIN", "AI", False),
        ("KOREAN_LITERAL", "는", True),
    ]
    assert _token_summary("123입니다") == [
        ("PLAIN", "123", False),
        ("KOREAN_LITERAL", "입니다", True),
    ]
    assert _token_summary("종로3가") == [
        ("KOREAN_LITERAL", "종로", True),
        ("PLAIN", "3", False),
        ("KOREAN_LITERAL", "가", True),
    ]


def test_compatibility_jamo_is_not_korean_literal_in_phase3() -> None:
    tokens = tokenize_immutable_spans("ㄱㄴㄷ")

    assert "".join(token.raw for token in tokens) == "ㄱㄴㄷ"
    assert all(token.kind != "KOREAN_LITERAL" for token in tokens)


def test_whitespace_sequences_are_space_lock_for_phase3_safety() -> None:
    assert _token_summary("전문 가") == [
        ("KOREAN_LITERAL", "전문", True),
        ("SPACE_LOCK", " ", True),
        ("KOREAN_LITERAL", "가", True),
    ]
    assert _token_summary("전문  가") == [
        ("KOREAN_LITERAL", "전문", True),
        ("SPACE_LOCK", "  ", True),
        ("KOREAN_LITERAL", "가", True),
    ]
    assert _token_summary("전문\n가") == [
        ("KOREAN_LITERAL", "전문", True),
        ("SPACE_LOCK", "\n", True),
        ("KOREAN_LITERAL", "가", True),
    ]


def test_korean_adjacent_terminal_punctuation_is_punct_lock() -> None:
    for mark in [",", ".", "!", "?"]:
        assert _token_summary(f"안녕하세요{mark}") == [
            ("KOREAN_LITERAL", "안녕하세요", True),
            ("PUNCT_LOCK", mark, True),
        ]


def test_non_korean_adjacent_comma_is_not_punct_lock() -> None:
    assert [kind for kind, _, _ in _token_summary("A,B")] == ["PLAIN"]
    assert [kind for kind, _, _ in _token_summary("123,456")] == ["PLAIN"]


def test_boundary_literals_are_preserved_without_bracket_claims() -> None:
    tokens = tokenize_immutable_spans("[[K:사용자입력]]")

    assert "".join(token.raw for token in tokens) == "[[K:사용자입력]]"
    assert any(token.kind == "BOUNDARY_LITERAL" and token.raw == "[" for token in tokens)
    assert any(token.kind == "BOUNDARY_LITERAL" and token.raw == ":" for token in tokens)
