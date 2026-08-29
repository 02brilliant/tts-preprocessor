from __future__ import annotations

import pytest

from engine.main import transform


def prod(text: str) -> str:
    return transform(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("01명", "01명"),
        ("01명에게", "01명에게"),
        ("09시", "아홉-시"),
        ("09시다", "아홉-시다"),
        ("07시 05분", "일곱-시 오분"),
        ("0시", "영-시"),
        ("00시", "영-시"),
        ("3 시", "삼 시"),
        ("3 시간", "삼 시간"),
        ("09:30", "아홉시 삼십분"),
        ("1만3천여 명", "일만삼천여 명"),
        ("1만3천여명", "일만삼천여명"),
        ("123 · 456", "백이십삼 · 사백오십육"),
        ("12 · 3 수치", "십이 · 삼 수치"),
        ("12. 3", "12. 3"),
        ("12 .3", "12 .3"),
        ("2~5시", "두-시에서 다섯-시"),
    ],
)
def test_user_approved_span_canonical_policy(text: str, expected: str) -> None:
    assert prod(text) == expected
