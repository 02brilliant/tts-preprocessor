from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "그리고, 우리는 결과를 확인했다",
        "그러나: 문제는 남아 있었다",
        "하지만; 테스트는 통과했다",
        "그런데. 결과가 달랐다",
        "따라서! 다음 단계를 진행한다",
    ],
)
def test_phase18b_existing_punctuation_blocks_new_comma(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "그리고우리는 결과를 확인했다",
        "그러나문제는 남아 있었다",
        "하지만테스트는 통과했다",
    ],
)
def test_phase18b_no_whitespace_boundary_blocks_comma(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[그리고 우리는 결과를 확인했다]", "그리고 우리는 결과를 확인했다"),
        ("메모는 [그리고 우리는 결과를 확인했다]입니다", "메모는 그리고 우리는 결과를 확인했다입니다"),
        ("(그리고 우리는 결과를 확인했다)", ""),
        ("메모는 (그리고 우리는 결과를 확인했다)입니다", "메모는 입니다"),
    ],
)
def test_phase18b_bracket_and_protected_blockers(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "그리고 http://x/y 를 확인했다",
        "그리고 path/to/file 을 확인했다",
        "그리고 code_like_token 을 확인했다",
    ],
)
def test_phase18b_url_path_code_like_blockers(text: str) -> None:
    assert transform(text) == text
