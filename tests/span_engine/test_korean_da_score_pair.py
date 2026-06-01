from __future__ import annotations

import pytest

from engine.main import transform_with_rollout


def _normalize(src: str) -> str:
    return transform_with_rollout(src, mode="span_default", include_debug=False)


def _claim_owners(src: str) -> list[str]:
    result = transform_with_rollout(src, mode="span_default", include_debug=True)
    claim_logs = result["span_debug"]["trace"]["claim_logs"]
    return [claim["owner"] for claim in claim_logs]


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("세트스코어는 2 대 1입니다.", "세트스코어는 이 대 일입니다."),
        ("점수는 2 대 1 이다.", "점수는 이 대 일 이다."),
        ("경기는 2대 1로 끝났다.", "경기는 이 대 일로 끝났다."),
    ],
)
def test_korean_da_score_pair_required_examples(src: str, expected: str) -> None:
    assert _normalize(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("스코어 2 대 1입니다.", "스코어 이 대 일입니다."),
        ("점수 2대1이었다.", "점수 이대일이었다."),
        ("세트스코어 2대 1이다.", "세트스코어 이 대 일이다."),
        ("세트스코어는 2대1이었다.", "세트스코어는 이대일이었다."),
        ("점수는 2대 1이다.", "점수는 이 대 일이다."),
    ],
)
def test_korean_da_score_pair_left_keyword(src: str, expected: str) -> None:
    assert _normalize(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("2 대 1 스코어였다.", "이 대 일 스코어였다."),
        ("2대1 점수였다.", "이대일 점수였다."),
        ("2대 1 세트스코어였다.", "이 대 일 세트스코어였다."),
    ],
)
def test_korean_da_score_pair_right_keyword(src: str, expected: str) -> None:
    assert _normalize(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("2 대 1의 스코어", "이 대 일의 스코어"),
        ("2대1의 점수", "이대일의 점수"),
        ("2대 1로 승리했다.", "이 대 일로 승리했다."),
        ("2대1로 이겼다.", "이대일로 이겼다."),
    ],
)
def test_korean_da_score_pair_bridge_context(src: str, expected: str) -> None:
    assert _normalize(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("3 대 1 승리", "삼 대 일 승리"),
        ("3 대 1의 스코어", "삼 대 일의 스코어"),
        ("스코어 3 대 1", "스코어 삼 대 일"),
    ],
)
def test_korean_da_score_pair_matches_colon_context_gate(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("차량 2대입니다.", "차량 두 대입니다."),
        ("장비 3대 추가", "장비 세 대 추가"),
        ("버스 10대 운행", "버스 열 대 운행"),
        ("장비 2대 이상", "장비 두 대 이상"),
        ("차량 2대 1대를 점검했다.", "차량 두 대 한 대를 점검했다."),
        ("장비 2대 1개를 추가했다.", "장비 두 대 한 개를 추가했다."),
    ],
)
def test_korean_da_score_pair_does_not_break_counter_da(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" not in _claim_owners(src)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("2 대 1이다.", "두 대 일이다."),
        ("2대1이다.", "이대일이다."),
        ("2대 1이다.", "두 대 일이다."),
    ],
)
def test_korean_da_score_pair_bare_forms_do_not_claim_without_context(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" not in _claim_owners(src)


@pytest.mark.parametrize(
    "src",
    [
        "점수는 0대1이다.",
        "점수는 01대1이다.",
        "점수는 1대01이다.",
        "점수는 1.5대2이다.",
        "점수는 1,000대2이다.",
        "점수는 +1대2이다.",
        "점수는 -1대2이다.",
        "점수는 1 대2이다.",
    ],
)
def test_korean_da_score_pair_invalid_forms_do_not_partial_score_claim(
    src: str,
) -> None:
    assert "korean_da_score_pair" not in _claim_owners(src)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("`2대1`", "`2대1`"),
        ("[2대1]", "2대1"),
        ("/path/2대1/log", "/path/2대1/log"),
        ('{"score":"2대1"}', '{"score":"2대1"}'),
        ("A2대1", "A2대1"),
        ("v2대1", "v2대1"),
    ],
)
def test_korean_da_score_pair_protected_contexts(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" not in _claim_owners(src)
