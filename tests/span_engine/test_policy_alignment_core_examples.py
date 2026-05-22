from __future__ import annotations

import pytest

from engine.span_engine import transform


CORE_POLICY_EXAMPLES = [
    ("6월", "유월"),
    ("10월", "시월"),
    ("2026년 6월 17일", "이천이십육년 유월 십칠일"),
    ("2025-13-03", "이공이오 일삼 공삼"),
    ("39명", "서른아홉 명"),
    ("40명", "사십 명"),
    ("101명", "백일 명"),
    ("140살", "백사십 살"),
    ("112명", "백십이 명"),
    ("119건", "백십구 건"),
    ("2대", "두 대"),
    ("40항목", "사십 항목"),
    ("101사례", "백일 사례"),
    (
        "12,345,678,901,234명",
        "십이조 삼천사백오십육억 칠천팔백구십만 천이백삼십사 명",
    ),
    ("제5차", "제 오차"),
    ("제 5차", "제 오차"),
    ("제15권", "제 십오권"),
    ("제2항목", "제 이항목"),
    ("K-푸드", "케이푸드"),
    ("K-푸드-v2", "K-푸드-v2"),
    ("K-2024", "K-2024"),
    ("K-1", "케이 원"),
    ("A-10C", "에이 십 씨"),
    ("A-3kg", "A-3kg"),
    ("B-2.5", "비 이쩜오"),
    ("pH 7.4", "피에이치 칠쩜사"),
    ("pH7.4test", "pH7.4test"),
    ("45m3", "사십오 세제곱미터"),
    ("45m3abc", "45m3abc"),
    ("90km/h", "시속 구십 킬로미터"),
    ("90km/hour", "90km/hour"),
    ("https://example.com/K-푸드", "https://example.com/K-푸드"),
]


@pytest.mark.parametrize(("source", "expected"), CORE_POLICY_EXAMPLES)
def test_core_policy_examples_align_with_transform(source: str, expected: str) -> None:
    assert transform(source) == expected
