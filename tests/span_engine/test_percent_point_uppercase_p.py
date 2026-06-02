from __future__ import annotations

import pytest

from engine.main import transform_with_rollout


def _prod(src: str) -> str:
    result = transform_with_rollout(
        src,
        mode="span_default",
        include_debug=False,
    )
    return getattr(result, "normalized_text", result)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (
            "전월 같은 조사보다 3%P 하락한 것입니다.",
            "전월 같은 조사보다 삼 퍼센트포인트 하락한 것입니다.",
        ),
        (
            "전월 같은 조사보다 3%P 하락한 것입니다. 반면 내각을 지지하지 않는다는 응답은 이십팔 퍼센트로 전월보다 2%P 상승했습니다.",
            "전월 같은 조사보다 삼 퍼센트포인트 하락한 것입니다.\n반면 내각을 지지하지 않는다는 응답은 이십팔 퍼센트로 전월보다 이 퍼센트포인트 상승했습니다.",
        ),
        ("3%P", "삼 퍼센트포인트"),
        ("3%p", "삼 퍼센트포인트"),
        ("3％P", "삼 퍼센트포인트"),
        ("3％p", "삼 퍼센트포인트"),
        ("3﹪P", "삼 퍼센트포인트"),
        ("3﹪p", "삼 퍼센트포인트"),
        ("2.5%P", "이쩜오 퍼센트포인트"),
        ("+2.5%P", "플러스 이쩜오 퍼센트포인트"),
        ("+2.5%p", "플러스 이쩜오 퍼센트포인트"),
        ("-2.5%P", "마이너스 이쩜오 퍼센트포인트"),
    ],
)
def test_percent_point_uppercase_p(src: str, expected: str) -> None:
    assert _prod(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("2.5%Pa", "2.5%Pa"),
        ("2.5%Point", "2.5%Point"),
        ("2.5％Point", "2.5％Point"),
        ("2.5﹪Point", "2.5﹪Point"),
    ],
)
def test_percent_point_uppercase_p_unsafe_tails_preserve(
    src: str, expected: str
) -> None:
    assert _prod(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("`3%P`", "`3%P`"),
        ("[3%P]", "3%P"),
        ("/path/3%P/log", "/path/3%P/log"),
        ('{"change":"3%P"}', '{"change":"3%P"}'),
        ("https://example.com?q=3%P", "https://example.com?q=3%P"),
    ],
)
def test_percent_point_uppercase_p_protected_contexts(
    src: str, expected: str
) -> None:
    assert _prod(src) == expected
