from __future__ import annotations

import re

import pytest

from engine.pipeline.transform_engine import transform_text


VIOLATION_SIGNATURE_PATTERNS = [
    r"에프티에 이",
    r"에이아가",
    r"전문이",
    r"있은",
    r"육천사백이 억",
    r"일 조",
    r"-[가-힣]+도",
    r"[가-힣]+~[0-9]",
    r"케가-",
    r"육 이칠",
    r"십이 일이",
    r"십이 삼",
]


REGRESSION_INPUTS = [
    "FTA 요건만 충족하면",
    "AI·반도체",
    "민관 전문가",
    "키울 수 있는 양날의 칼",
    "6402억 달러",
    "-1.3도",
    "3~8cm",
    "K-푸드·K-뷰티·K-POP",
    "12·12 사태",
    "FTA 요건만 충족하면 AI·디지털 교육과 K-푸드 전략은 6402억 달러 규모로 1∼11월 동안 유지된다",
]


@pytest.mark.parametrize("text", REGRESSION_INPUTS)
def test_typed_surface_engine_forbids_known_violation_signatures(text: str):
    actual = transform_text(text)
    for pattern in VIOLATION_SIGNATURE_PATTERNS:
        assert re.search(pattern, actual) is None, f"input={text!r} pattern={pattern!r} actual={actual!r}"
