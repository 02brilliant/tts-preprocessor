from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "1·4분기 2·4분기 1·2월 3·4일",
            "일·사분기 이·사분기 일·이월 삼·사일",
        ),
        (
            "1·사분기 2·사분기 1·이월 삼 사일",
            "일·사분기 이·사분기 일·이월 삼 사일",
        ),
        ("12·3 7·25 123·456", "일이·삼 칠·이오 일이삼·사오육"),
        ("KGM-체리자동차 KG그룹", "케이지엠-체리자동차 케이지그룹"),
        ("한화M&S는 R&D기반", "한화엠앤에스는 알앤디기반"),
        ("㈜한화와 ㈜ABC", "주식회사 한화와 주식회사 에이비씨"),
        ("20~30억원, 20~30만원, 20~30", "이십에서 삼십억원, 이십에서 삼십만원, 이십에서 삼십"),
        (
            "1번째 2번째 3번째 4번째 5번째 39번째 40번째",
            "첫 번째 두 번째 세 번째 네 번째 다섯 번째 서른아홉 번째 사십 번째",
        ),
        ("1천㎞ 수십ｍ 수백㎞", "일천 킬로미터 수십 미터 수백 킬로미터"),
    ],
)
def test_requested_reading_expansions(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_middle_dot_korean_temporal_literals_use_general_number_fallback() -> None:
    output = transform_with_trace("1·사분기 2·사분기 1·이월")

    assert output.normalized_text == "일·사분기 이·사분기 일·이월"
    assert [
        (claim.owner, claim.reason, claim.span.start, claim.span.end)
        for claim in output.trace.claim_logs
    ] == [
        ("number", "phase7_minimal_ascii_number", 0, 1),
        ("number", "phase7_minimal_ascii_number", 6, 7),
        ("number", "phase7_minimal_ascii_number", 12, 13),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "https://example.com/KGM-체리",
        "/tmp/M&S/report",
        "code_KGM-체리",
    ],
)
def test_requested_acronym_expansion_keeps_protected_or_code_like_tokens(text: str) -> None:
    assert transform(text) == text


def test_parenthesis_policy_still_elides_the_complete_parenthesized_content() -> None:
    assert (
        transform("LG(003550)의 인공지능(AI) 플랫폼 ‘엑사원(EXAONE)’이")
        == "엘지의 인공지능 플랫폼 ‘엑사원’이"
    )
