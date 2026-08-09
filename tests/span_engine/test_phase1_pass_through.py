from __future__ import annotations

import pytest

from engine.prosody.paragraph import split_paragraphs
from engine.span_engine import transform, transform_with_trace


TRANSFORM_CASES = [
    ("", ""),
    ("안녕하세요", "안녕하세요"),
    ("전문  가", "전문  가"),
    ("안녕하세요,", "안녕하세요,"),
    ("안녕하세요 , 반갑습니다", "안녕하세요 , 반갑습니다"),
    ("AI는 123입니다", "에이아이는 백이십삼입니다"),
    ("회의는 13:05에 시작한다", "회의는 십삼시 오분에 시작한다"),
    ("12.3 비상계엄", "십이삼 비상계엄"),
    ("3~8cm", "삼에서 팔 센티미터"),
    ("가격은 [3kg]입니다", "가격은 3kg입니다"),
    ("비용은 (약) 3만원입니다", "비용은 삼만 원입니다"),
    ("FTA은 적용됐다", "에프티에이는 적용됐다"),
    ("AI이 적용됐다", "에이아이이 적용됐다"),
    ("유로을 입력했다", "유로을 입력했다"),
    ("종로3가", "종로삼가"),
    ("1-1-9", "일 일 구"),
    ("123-456-7890", "일이삼 사오육 칠팔구공"),
    ("pH 7.4", "피에이치 칠쩜사"),
    ("€50을 냈다", "오십 유로를 냈다"),
    ("-2.5℃", "영하 이쩜오도"),
    ("ㄱㄴㄷ", "기역 니은 디귿"),
    ("전문\n가", "전문 가"),
    ("emoji 😀 테스트", "emoji 😀 테스트"),
    ("zero\u200bwidth", "zero\u200bwidth"),
    ("[[K:사용자입력]]", "[K:사용자입력]"),
    ("{{S:사용자입력}}", "{{S:사용자입력}}"),
]


@pytest.mark.parametrize(("text", "expected"), TRANSFORM_CASES)
def test_transform_applies_only_phase7_supported_owners(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(("text", "expected"), TRANSFORM_CASES)
def test_transform_with_trace_normalized_text_matches_expected(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    rendered = "".join(piece.text for piece in output.render_pieces)
    if "[" in text or "(" in text:
        assert rendered != ""
    else:
        assert split_paragraphs(rendered) == expected
