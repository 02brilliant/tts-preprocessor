from __future__ import annotations

import pytest

from engine.main import transform, transform_debug


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5분 뒤", "오분 뒤"),
        ("손님 5분이 도착했다", "손님 다섯 분이 도착했다"),
        ("참석자 12분을 모셨다", "참석자 열두 분을 모셨다"),
        ("5분이 남았다", "오분이 남았다"),
        ("3번 버스", "삼번 버스"),
        ("총 3번 시도했다", "총 세 번 시도했다"),
        ("3번씩 반복했다", "세 번씩 반복했다"),
        ("3번 확인했다", "세 번 확인했다"),
        ("평점 3점", "평점 삼 점"),
        ("평점은 3점이었다", "평점은 삼 점이었다"),
        ("작품 3점을 전시했다", "작품 세 점을 전시했다"),
        ("3점이 공개됐다", "세 점이 공개됐다"),
        ("3.5점", "삼쩜오 점"),
        ("3조 원", "삼조 원"),
        ("학생을 3조로 나눴다", "학생을 세 조로 나눴다"),
        ("총 3조를 편성했다", "총 세 조를 편성했다"),
        ("3조가 발표했다", "세 조가 발표했다"),
        ("제3조", "제3조"),
    ],
)
def test_contextual_core_unit_canonical(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_multiple_meanings_and_units_can_coexist() -> None:
    text = (
        "손님 5분이 도착했고 회의는 5분 뒤 시작했다. "
        "3번 버스에서 총 3번 재생했고 작품 3점을 전시했으며 평점 3점을 기록했다."
    )
    assert transform(text) == (
        "손님 다섯 분이 도착했고 회의는 오분 뒤 시작했다. "
        "삼번 버스에서 총 세 번 재생했고 작품 세 점을 전시했으며 평점 삼 점을 기록했다."
    )


@pytest.mark.parametrize(
    "text",
    [
        "01분",
        "+3번",
        "-3점",
        "1,00조",
        "3A번",
        "1.5분",
        "2.5번",
    ],
)
def test_contextual_core_malformed_is_atomic_defer(text: str) -> None:
    debug = transform_debug(text)
    assert debug["normalized_text"] == text
    claims = debug["debug"]["trace"]["claim_logs"]
    assert len(claims) == 1
    assert claims[0]["owner"] == "contextual_number_unit"
    assert claims[0]["claim_type"] == "preserve"


def test_valid_decimal_large_unit_keeps_existing_large_unit_owner() -> None:
    debug = transform_debug("1.5조")
    assert debug["normalized_text"] == "일쩜오 조"
    assert [
        claim["owner"]
        for claim in debug["debug"]["trace"]["claim_logs"]
    ] == ["large_unit_atomic"]
    assert debug["debug"]["trace"]["contextual_decision_logs"] == []


@pytest.mark.parametrize(
    "text",
    [
        "`손님 5분`",
        "/path/학생3조/file",
        '{"value":"작품 3점"}',
        "H100_3번.json",
        "[3번 확인했다]",
    ],
)
def test_contextual_core_protected_surfaces_do_not_run(text: str) -> None:
    debug = transform_debug(text)
    assert debug["debug"]["trace"]["contextual_decision_logs"] == []


@pytest.mark.parametrize(
    ("text", "unit", "decision", "semantic_type"),
    [
        ("손님 5분이 도착했다", "분", "confirmed", "honorific_person_count"),
        ("5분이 남았다", "분", "confirmed", "duration_minute"),
        ("3번 버스", "번", "confirmed", "identifier"),
        ("3번 확인했다", "번", "confirmed", "occurrence"),
        ("작품 3점을 전시했다", "점", "confirmed", "item_count"),
        ("3점이 공개됐다", "점", "confirmed", "item_count"),
        ("학생을 3조로 나눴다", "조", "confirmed", "group_count"),
        ("3조가 발표했다", "조", "confirmed", "group_count"),
    ],
)
def test_contextual_core_debug_decision_log(
    text: str, unit: str, decision: str, semantic_type: str
) -> None:
    debug = transform_debug(text)
    logs = debug["debug"]["trace"]["contextual_decision_logs"]
    assert len(logs) == 1
    assert logs[0]["unit"] == unit
    assert logs[0]["decision"] == decision
    assert logs[0]["semantic_type"] == semantic_type
    assert logs[0]["reentry_blocked"] is True
    assert logs[0]["actual_final_output"] == debug["normalized_text"]


@pytest.mark.parametrize(
    ("text", "owner"),
    [
        ("5분 뒤", "duration"),
        ("3.5점", "decimal_registered_suffix"),
        ("3조 원", "large_unit_atomic"),
    ],
)
def test_existing_specific_owner_precedence_is_unchanged(
    text: str, owner: str
) -> None:
    debug = transform_debug(text)["debug"]
    assert [claim["owner"] for claim in debug["trace"]["claim_logs"]] == [owner]
    assert debug["trace"]["contextual_decision_logs"] == []
