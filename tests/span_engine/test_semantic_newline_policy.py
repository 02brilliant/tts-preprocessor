from __future__ import annotations

import pytest

from engine.main import transform
from engine.prosody.paragraph import normalize_user_newline_semantics


def test_single_non_terminal_newline_joins_as_one_sentence() -> None:
    newlines = "\n"
    assert transform(f"지역에 대해{newlines}미국의 새 전략") == "지역에 대해 미국의 새 전략"


@pytest.mark.parametrize("newlines", ["\n\n", "\n\n\n", "\r\n\r\n"])
def test_blank_line_adds_comma_before_joining_non_terminal_lines(newlines: str) -> None:
    assert transform(f"국내 증시 반등 시도  {newlines}  -키움증권은 전망했다.") == (
        "국내 증시 반등 시도, -키움증권은 전망했다."
    )


def test_blank_line_does_not_duplicate_existing_comma() -> None:
    assert transform("국내 증시 반등 시도,\n\n-키움증권은 전망했다.") == (
        "국내 증시 반등 시도, -키움증권은 전망했다."
    )


def test_comma_is_preserved_while_visual_newline_joins() -> None:
    assert transform("오키나와,\n타이완") == "오키나와, 타이완"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("지역에 대해  \n   미국의 새 전략", "지역에 대해 미국의 새 전략"),
        ("오키나와,\n   타이완", "오키나와, 타이완"),
        ('"인용문  \n   계속"', '"인용문 계속"'),
    ],
)
def test_visual_newline_join_collapses_only_boundary_whitespace(
    text: str, expected: str
) -> None:
    assert normalize_user_newline_semantics(text) == expected
    assert transform(text) == expected


def test_in_line_spaces_without_a_newline_remain_source_exact() -> None:
    assert transform("한글  사이") == "한글  사이"


def test_period_before_newline_keeps_existing_paragraph_boundary() -> None:
    assert transform("첫 문장입니다.\n다음 문장입니다.") == "첫 문장입니다.\n\n다음 문장입니다."


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('"인용.\n쉼표,\n계속"\n다음', '"인용. 쉼표, 계속"\n\n다음'),
        ("'인용.\n쉼표,\n계속'\n다음", "'인용. 쉼표, 계속'\n\n다음"),
    ],
)
def test_matched_ascii_quote_interior_joins_but_closing_quote_keeps_boundary(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_ascii_apostrophe_does_not_enable_quote_mode() -> None:
    assert transform("그는 don't\nstop이라고 말했다") == "그는 don't stop이라고 말했다"


@pytest.mark.parametrize(
    "text",
    [
        "```json\n{\n  \"count\": 25\n}\n```",
        "`코드\n25` 뒤",
        '{\n  "count": 25\n}',
    ],
)
def test_protected_code_newlines_remain_source_exact(text: str) -> None:
    assert normalize_user_newline_semantics(text) == text
    assert transform(text) == text


def test_newline_is_joined_before_language_gate_line_classification() -> None:
    assert transform("설명은\nKGM은 2일에 발표했다") == "설명은 케이지엠은 이일에 발표했다"


def test_user_supplied_multiline_article_example() -> None:
    text = '''"중국을 자극하진 않으면서
'적절한 평화'를 유지하겠다"

인도-태평양 지역에 대해
미국의 새 국방전략에 담긴 내용입니다.

이를 위해 콜비 차관은
일본 규슈와 오키나와,
타이완, 필리핀을 잇는
'제1 도련선'을 지목했습니다.

미국의 대중국 봉쇄선입니다.

타이완 유사시와 같이
힘의 균형이 깨지는 상황이
생기지 않도록
중국을 견제하겠다는 건데,

중국 바로 옆에 주둔한
주한미군의 역할도
변할 수밖에 없습니다.'''

    expected = '''"중국을 자극하진 않으면서 '적절한 평화'를 유지하겠다"

인도-태평양 지역에 대해 미국의 새 국방전략에 담긴 내용입니다.

이를 위해 콜비 차관은 일본 규슈와 오키나와, 타이완, 필리핀을 잇는 '제일 도련선'을 지목했습니다.

미국의 대중국 봉쇄선입니다.

타이완 유사시와 같이 힘의 균형이 깨지는 상황이 생기지 않도록 중국을 견제하겠다는 건데, 중국 바로 옆에 주둔한 주한미군의 역할도 변할 수밖에 없습니다.'''

    assert transform(text) == expected
