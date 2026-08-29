from __future__ import annotations

import pytest

from engine.main import transform as transform_text
from tests._policy_case import TextCase, assert_exact


PARSER_CONTEXT_CASES = (
    TextCase(
        case_id="parser-context-time-in-korean-sentence",
        text="회의는 13:05에 시작한다",
        expected="회의는 십삼시 오분에 시작한다",
        rule="parser context / time",
        reason="time parser는 한글 문장 안에서도 좌우 문맥을 읽고 숫자만 해석해야 한다.",
        classification="parser",
    ),
    TextCase(
        case_id="parser-context-date-in-korean-sentence",
        text="일정은 2025년 1월 3일이다",
        expected="일정은 이천이십오년 일월 삼일이다",
        rule="parser context / date",
        reason="date parser는 한글 주변 context를 읽되 한글 literal 자체는 바꾸지 않아야 한다.",
        classification="parser",
    ),
    TextCase(
        case_id="parser-context-range-in-korean-sentence",
        text="시편은 3~8cm다",
        expected="시편은 삼에서 팔-센티미터다",
        rule="parser context / range + unit",
        reason="range parser는 한글 명사 문맥 안에서도 숫자와 기호만 구조적으로 해석해야 한다.",
        classification="parser",
    ),
    TextCase(
        case_id="parser-context-currency-in-korean-sentence",
        text="비용은 €1,234.56이다",
        expected="비용은 천이백삼십사쩜오육-유로이다",
        rule="parser context / currency",
        reason="currency parser는 한글 predicate 문맥을 읽어도 한글 literal을 rewrite하지 않는다.",
        classification="parser",
    ),
    TextCase(
        case_id="parser-context-event-reading-in-korean-sentence",
        text="12.3 비상계엄은 유지한다",
        expected="십이삼 비상계엄은 유지한다",
        rule="parser context / dotted event",
        reason="event keyword context가 있으면 dotted event owner가 숫자 surface를 읽고 한글 문맥은 보존한다.",
        classification="parser",
    ),
)


@pytest.mark.parametrize("case", PARSER_CONTEXT_CASES, ids=lambda case: case.case_id)
def test_parser_context_reading_in_korean_sentences(case: TextCase):
    assert_exact(transform_text(case.text), case)
