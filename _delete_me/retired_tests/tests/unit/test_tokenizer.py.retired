"""This file includes migrated tests from *_cases.py to ensure pytest collection."""

from engine.tokenizer import token_types
from engine.tokenizer.tokenizer import tokenize


def test_space_is_preserved():
    text = "오늘  매출"

    tokens = tokenize(text)

    assert [token.text for token in tokens] == ["오늘", "  ", "매출"]
    assert [token.kind for token in tokens] == [
        token_types.WORD_KO,
        token_types.SPACE,
        token_types.WORD_KO,
    ]


def test_newline_is_preserved():
    text = "오늘\n내일"

    tokens = tokenize(text)

    assert [token.text for token in tokens] == ["오늘", "\n", "내일"]
    assert tokens[1].kind == token_types.NEWLINE
    assert tokens[2].line == 2
    assert tokens[2].column == 1


def test_punctuation_is_preserved():
    text = '안녕, 정말 좋다.'

    tokens = tokenize(text)

    assert [token.text for token in tokens] == ["안녕", ",", " ", "정말", " ", "좋다", "."]
    assert tokens[1].kind == token_types.PUNCT
    assert tokens[-1].kind == token_types.PUNCT


def test_offsets_are_exact():
    text = "가 나\n다."

    tokens = tokenize(text)

    assert [(token.text, token.start, token.end) for token in tokens] == [
        ("가", 0, 1),
        (" ", 1, 2),
        ("나", 2, 3),
        ("\n", 3, 4),
        ("다", 4, 5),
        (".", 5, 6),
    ]


def test_joined_token_text_matches_original():
    text = "오늘 매출은 12300원이며,\n내일은 AI가 발표한다."

    tokens = tokenize(text)

    assert "".join(token.text for token in tokens) == text


def test_basic_classification():
    text = "오늘 ABC abc 123 AI가 123원 @"

    tokens = tokenize(text)

    values = [
        (token.text, token.kind)
        for token in tokens
        if (token.kind == token_types.SPACE) == False
    ]
    assert values == [
        ("오늘", token_types.WORD_KO),
        ("ABC", token_types.WORD_EN_UPPER),
        ("abc", token_types.WORD_EN_LOWER),
        ("123", token_types.NUMBER),
        ("AI가", token_types.MIXED),
        ("123원", token_types.MIXED),
        ("@", token_types.SYMBOL),
    ]


def test_reference_example_conditions():
    text = "오늘 매출은 12300원이며,\n내일은 AI가 발표한다."

    tokens = tokenize(text)
    token_map = [(token.text, token.kind) for token in tokens]

    assert token_map.count((",", token_types.PUNCT)) == 1
    assert token_map.count(("\n", token_types.NEWLINE)) == 1
    assert token_map.count(("AI가", token_types.MIXED)) == 1
    assert [
        (token.text, token.kind)
        for token in tokenize("AI")
    ] == [("AI", token_types.WORD_EN_UPPER)]
    assert "".join(token.text for token in tokens) == text


def test_adjacent_token_sequences_remain_available_for_multi_token_parsing():
    usb_tokens = tokenize("USB 3.0")
    assert [token.text for token in usb_tokens] == ["USB", " ", "3", ".", "0"]

    ph_tokens = tokenize("pH 7.4")
    assert [token.text for token in ph_tokens] == ["pH", " ", "7", ".", "4"]

    usd_tokens = tokenize("USD 100")
    assert [token.text for token in usd_tokens] == ["USD", " ", "100"]
