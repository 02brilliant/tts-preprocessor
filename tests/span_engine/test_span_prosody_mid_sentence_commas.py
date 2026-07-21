from __future__ import annotations

import pytest

from engine.main import transform


def _production_text(src: str) -> str:
    result = transform(src)
    if isinstance(result, str):
        return result
    if hasattr(result, "normalized_text"):
        return result.normalized_text
    return result["normalized_text"]


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (
            "매출은 늘었습니다 하지만 영업이익은 줄었습니다.",
            "매출은 늘었습니다, 하지만 영업이익은 줄었습니다.",
        ),
        (
            "전월보다 하락했습니다 반면 응답률은 상승했습니다.",
            "전월보다 하락했습니다, 반면 응답률은 상승했습니다.",
        ),
        (
            "수요가 감소했습니다 이에 따라 가격도 하락했습니다.",
            "수요가 감소했습니다, 이에 따라 가격도 하락했습니다.",
        ),
        (
            "정부는 추가 대책을 검토하고 있습니다 다만 구체적인 시행 시점은 아직 정해지지 않았습니다.",
            "정부는 추가 대책을 검토하고 있습니다, 다만 구체적인 시행 시점은 아직 정해지지 않았습니다.",
        ),
    ],
)
def test_mid_sentence_discourse_marker_commas(src: str, expected: str) -> None:
    assert _production_text(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (
            "매출은 늘었습니다, 하지만 영업이익은 줄었습니다.",
            "매출은 늘었습니다, 하지만 영업이익은 줄었습니다.",
        ),
        (
            "매출은 늘었습니다. 하지만 영업이익은 줄었습니다.",
            "매출은 늘었습니다. 하지만, 영업이익은 줄었습니다.",
        ),
    ],
)
def test_mid_sentence_commas_do_not_duplicate_existing_punctuation(
    src: str, expected: str
) -> None:
    assert _production_text(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("하지만 나는 갔다.", "하지만, 나는 갔다."),
        ("반면 효과는 작았다.", "반면 효과는 작았다."),
        ("주가는 상승했다.", "주가는 상승했다."),
        ("오늘은 비가 왔다.", "오늘은 비가 왔다."),
    ],
)
def test_mid_sentence_commas_do_not_overinsert_short_sentences(
    src: str, expected: str
) -> None:
    assert _production_text(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (
            "`하지만 3%P` 다음 문장입니다.",
            "`하지만 3%P` 다음 문장입니다.",
        ),
        (
            "[하지만 3%P] 다음 문장입니다.",
            "하지만 3%P 다음 문장입니다.",
        ),
        (
            '{"text":"하지만 3%P"} 다음 문장입니다.',
            '{"text":"하지만 3%P"} 다음 문장입니다.',
        ),
        (
            "값은 1,000.5원입니다 하지만 변동폭은 2.5%P입니다.",
            "값은 천쩜오 원입니다, 하지만 변동폭은 이쩜오 퍼센트포인트입니다.",
        ),
        (
            "점수는 2대1입니다 하지만 2.1대 1.5는 아닙니다.",
            "점수는 이대일입니다, 하지만 이쩜일 대 일쩜오는 아닙니다.",
        ),
        (
            "비율은 1/3대 2/5입니다 반면 값은 3.14입니다.",
            "비율은 삼분의 일 대 오분의 이입니다, 반면 값은 삼쩜일사입니다.",
        ),
    ],
)
def test_mid_sentence_commas_protected_and_numeric_safety(
    src: str, expected: str
) -> None:
    assert _production_text(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("하지만 나는 갔다.", "하지만, 나는 갔다."),
        ("그러나 결과는 달랐다.", "그러나, 결과는 달랐다."),
        (
            "매출은 늘었습니다. 하지만 영업이익은 줄었습니다.",
            "매출은 늘었습니다. 하지만, 영업이익은 줄었습니다.",
        ),
    ],
)
def test_existing_start_connector_comma_behavior_is_preserved(
    src: str, expected: str
) -> None:
    assert _production_text(src) == expected
