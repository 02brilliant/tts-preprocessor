from __future__ import annotations

from dataclasses import dataclass

from engine.tokenizer import token_types


_PUNCT_CHARS = {
    ",",
    ".",
    "?",
    "!",
    ":",
    ";",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    '"',
    "'",
    "“",
    "”",
    "‘",
    "’",
    "「",
    "」",
    "『",
    "』",
    "〈",
    "〉",
    "《",
    "》",
    "…",
}


@dataclass(frozen=True, slots=True)
class Token:
    text: str
    kind: str
    start: int
    end: int
    line: int
    column: int


def _is_hangul(char: str) -> bool:
    code = ord(char)
    return (
        0xAC00 <= code <= 0xD7A3
        or 0x1100 <= code <= 0x11FF
        or 0x3130 <= code <= 0x318F
        or 0xA960 <= code <= 0xA97F
        or 0xD7B0 <= code <= 0xD7FF
    )


def _char_group(char: str) -> str:
    if char == "\n":
        return token_types.NEWLINE
    if char.isspace():
        return token_types.SPACE
    if char in _PUNCT_CHARS:
        return token_types.PUNCT
    if _is_hangul(char):
        return "KO"
    if "A" <= char <= "Z":
        return "EN_UPPER"
    if "a" <= char <= "z":
        return "EN_LOWER"
    if char.isdigit():
        return "NUMBER"
    if char.isprintable():
        return token_types.SYMBOL
    return token_types.UNKNOWN


def _classify_word(text: str) -> str:
    seen_ko = False
    seen_upper = False
    seen_lower = False
    seen_number = False

    for char in text:
        if _is_hangul(char):
            seen_ko = True
        elif "A" <= char <= "Z":
            seen_upper = True
        elif "a" <= char <= "z":
            seen_lower = True
        elif char.isdigit():
            seen_number = True
        else:
            return token_types.MIXED

    kinds = seen_ko + seen_upper + seen_lower + seen_number
    if kinds > 1:
        return token_types.MIXED
    if seen_ko:
        return token_types.WORD_KO
    if seen_upper:
        return token_types.WORD_EN_UPPER
    if seen_lower:
        return token_types.WORD_EN_LOWER
    if seen_number:
        return token_types.NUMBER
    return token_types.UNKNOWN


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    column = 1

    while i < len(text):
        start = i
        start_line = line
        start_column = column
        group = _char_group(text[i])

        if group in {"KO", "EN_UPPER", "EN_LOWER", "NUMBER"}:
            j = i + 1
            while j < len(text):
                next_group = _char_group(text[j])
                if next_group not in {"KO", "EN_UPPER", "EN_LOWER", "NUMBER"}:
                    break
                j += 1

            token_text = text[i:j]
            token_kind = _classify_word(token_text)
        elif group in {token_types.SPACE, token_types.NEWLINE}:
            j = i + 1
            while j < len(text) and _char_group(text[j]) == group:
                j += 1

            token_text = text[i:j]
            token_kind = group
        else:
            j = i + 1
            token_text = text[i:j]
            token_kind = group

        tokens.append(
            Token(
                text=token_text,
                kind=token_kind,
                start=start,
                end=j,
                line=start_line,
                column=start_column,
            )
        )

        for char in token_text:
            if char == "\n":
                line += 1
                column = 1
            else:
                column += 1

        i = j

    return tokens
