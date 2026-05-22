from __future__ import annotations

from engine.span_engine import transform


def test_phase18c_existing_single_newline_is_preserved() -> None:
    text = "첫 문장입니다.\n두 번째 문장입니다."

    assert transform(text) == text


def test_phase18c_existing_double_newline_is_preserved() -> None:
    text = "첫 문장입니다.\n\n두 번째 문장입니다."

    assert transform(text) == text


def test_phase18c_existing_newline_not_expanded_by_comma_adapter() -> None:
    text = "그리고 우리는 결과를 확인했다.\n그러나 문제는 남아 있었다."
    output = transform(text)

    assert output == "그리고, 우리는 결과를 확인했다.\n그러나, 문제는 남아 있었다."
    assert "\n\n" not in output
