from __future__ import annotations

import pytest

from engine.main import transform_with_rollout


def _production_text(src: str) -> str:
    result = transform_with_rollout(
        src,
        mode="span_default",
        include_debug=False,
    )
    if isinstance(result, str):
        return result
    if hasattr(result, "normalized_text"):
        return result.normalized_text
    return result["normalized_text"]


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("오늘 아침 우리는 출발했습니다.", "오늘 아침, 우리는 출발했습니다."),
        ("내일 서울에서 기자회견이 열립니다.", "내일 서울에서, 기자회견이 열립니다."),
        ("회의를 마치고 나서 우리는 이동했습니다.", "회의를 마치고 나서, 우리는 이동했습니다."),
        ("조사가 끝난 뒤 결과를 발표했습니다.", "조사가 끝난 뒤, 결과를 발표했습니다."),
        ("사과와 배와 포도 그리고 귤을 샀다.", "사과와 배와 포도, 그리고 귤을 샀다."),
    ],
)
def test_span_prosody_extra_positive(src: str, expected: str) -> None:
    assert _production_text(src) == expected


def test_span_prosody_extra_budget_selects_limited_candidates() -> None:
    src = "오늘 아침 우리는 회의를 마치고 나서 곧바로 서울로 이동했습니다 하지만 오후 일정은 취소됐습니다."
    expected = "오늘 아침 우리는 회의를 마치고 나서 곧바로 서울로 이동했습니다, 하지만 오후 일정은 취소됐습니다."

    assert _production_text(src) == expected


@pytest.mark.parametrize(
    "src",
    [
        "오늘 회의는 예정대로 진행됩니다.",
        "올해 실적은 크게 개선됐습니다.",
        "사람들 가운데 일부는 반대했습니다.",
        "뒤쪽 창문을 닫았습니다.",
        "경우의 수를 계산했습니다.",
    ],
)
def test_span_prosody_extra_avoids_false_positives(src: str) -> None:
    assert _production_text(src) == src


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (
            "`오늘 아침 우리는 출발했습니다` 다음 문장입니다.",
            "`오늘 아침 우리는 출발했습니다` 다음 문장입니다.",
        ),
        (
            '{"text":"회의를 마치고 나서"} 다음 문장입니다.',
            '{"text":"회의를 마치고 나서"} 다음 문장입니다.',
        ),
        ("/path/오늘 아침/log입니다.", "/path/오늘 아침/log입니다."),
        (
            "값은 1,000.5원입니다 오늘 아침 변동폭은 2.5%P였습니다.",
            "값은 천쩜오 원입니다 오늘 아침 변동폭은 이쩜오 퍼센트포인트였습니다.",
        ),
    ],
)
def test_span_prosody_extra_protected_and_owner_surfaces(
    src: str, expected: str
) -> None:
    assert _production_text(src) == expected
