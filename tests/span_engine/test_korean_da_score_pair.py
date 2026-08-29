from __future__ import annotations

import pytest

from engine.main import transform, transform_debug


def _normalize(src: str) -> str:
    return transform(src)


def _claim_owners(src: str) -> list[str]:
    result = transform_debug(src)
    claim_logs = result["debug"]["trace"]["claim_logs"]
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
        ("차량 2대입니다.", "차량 두-대입니다."),
        ("장비 3대 추가", "장비 세-대 추가"),
        ("버스 10대 운행", "버스 열-대 운행"),
        ("장비 2대 이상", "장비 두-대 이상"),
        ("차량 2대 1대를 점검했다.", "차량 두-대 한-대를 점검했다."),
        ("장비 2대 1개를 추가했다.", "장비 두-대 한-개를 추가했다."),
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
        (
            "점수는 2 대 1 입니다. 3 대 1은 아닙니다. 내일은 4대 3일까요?",
            "점수는 이 대 일 입니다. 삼 대 일은 아닙니다. 내일은 사 대 삼일까요?",
        ),
        ("2 대 1이다.", "이 대 일이다."),
        ("2 대 1 입니다.", "이 대 일 입니다."),
        ("2대1이다.", "이대일이다."),
        ("2대 1이다.", "이 대 일이다."),
        ("3 대 1은 아닙니다.", "삼 대 일은 아닙니다."),
        ("3대1은 아닙니다.", "삼대일은 아닙니다."),
        ("4대 3일까요?", "사 대 삼일까요?"),
        ("4 대 3일까요?", "사 대 삼일까요?"),
        ("4대3일까요?", "사대삼일까요?"),
        ("2 대 1.", "이 대 일."),
        ("2대1?", "이대일?"),
        ("2대 1, 다시 말해 3대 1은 아닙니다.", "이 대 일, 다시 말해 삼 대 일은 아닙니다."),
    ],
)
def test_korean_da_score_pair_independent_right_number_gate(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" in _claim_owners(src)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("2.1대 1.5", "이쩜일 대 일쩜오"),
        ("2.1대 1.5다", "이쩜일 대 일쩜오다"),
        ("1/3대 2/5", "삼분의 일 대 오분의 이"),
        ("+2대 -1", "플러스 이 대 마이너스 일"),
        ("0대1이다.", "영대일이다."),
        ("1,000대2", "천 대 이"),
        ("1,000.5대2.5", "천쩜오 대 이쩜오"),
        ("+2.5대-1.5", "플러스 이쩜오 대 마이너스 일쩜오"),
        ("2.1대1.5", "이쩜일 대 일쩜오"),
        ("1/3대2/5", "삼분의 일 대 오분의 이"),
        ("+2대-1", "플러스 이 대 마이너스 일"),
    ],
)
def test_korean_da_score_pair_readable_numeric_operands(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" in _claim_owners(src)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("2대1", "이대일"),
        ("2대 1", "이 대 일"),
        ("2 대 1", "이 대 일"),
        ("2.1대1.5", "이쩜일 대 일쩜오"),
        ("1/3대2/5", "삼분의 일 대 오분의 이"),
        ("+2대-1", "플러스 이 대 마이너스 일"),
    ],
)
def test_korean_da_score_pair_compact_rendering_only_for_plain_integer_compact_form(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" in _claim_owners(src)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("세트스코어는 2 대 1입니다.", "세트스코어는 이 대 일입니다."),
        ("점수는 2 대 1 이다.", "점수는 이 대 일 이다."),
        ("경기는 2대 1로 끝났다.", "경기는 이 대 일로 끝났다."),
        ("스코어 2대1이었다.", "스코어 이대일이었다."),
        ("2대1의 점수", "이대일의 점수"),
        ("2대 1로 승리했다.", "이 대 일로 승리했다."),
    ],
)
def test_korean_da_score_pair_existing_keyword_gate_still_works(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" in _claim_owners(src)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("차량은 2대 1입니다.", "차량은 이 대 일입니다."),
        ("장비는 3대 1일까요?", "장비는 삼 대 일일까요?"),
        ("카메라는 4 대 3은 아닙니다.", "카메라는 사 대 삼은 아닙니다."),
    ],
)
def test_korean_da_score_pair_left_context_does_not_block_independent_right_number(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" in _claim_owners(src)


@pytest.mark.parametrize(
    "src",
    [
        "차량 2대 1대를 점검했다.",
        "장비 2대 1개를 추가했다.",
        "인원은 2대 1명입니다.",
        "중량은 2대 1kg입니다.",
        "비율은 2대 1%입니다.",
        "금액은 2대 1원입니다.",
        "배율은 2대 1배입니다.",
        "시간은 2대 1시간입니다.",
        "기간은 2대 1분입니다.",
        "중량은 2.1대 1.5kg입니다.",
        "비율은 2.1대 1.5%입니다.",
        "금액은 2.1대 1.5원입니다.",
        "배율은 2.1대 1.5배입니다.",
        "금액은 +2대 -1원입니다.",
        "기간은 1/3대 2/5시간입니다.",
    ],
)
def test_korean_da_score_pair_blocks_when_right_side_forms_registered_owner_surface(
    src: str,
) -> None:
    assert "korean_da_score_pair" not in _claim_owners(src)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("내일은 4대 3일까요?", "내일은 사 대 삼일까요?"),
        ("결과는 2대 1이다.", "결과는 이 대 일이다."),
        ("결과는 2대1이었다.", "결과는 이대일이었다."),
        ("결과는 2 대 1입니다.", "결과는 이 대 일입니다."),
    ],
)
def test_korean_da_score_pair_does_not_misclassify_copula_tail_as_day_suffix(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" in _claim_owners(src)


@pytest.mark.parametrize(
    "src",
    [
        "점수는 01대1이다.",
        "점수는 1대01이다.",
        "점수는 001대1이다.",
        "점수는 .5대1이다.",
        "점수는 1.대2이다.",
        "점수는 1,00대2이다.",
        "점수는 1,0000대2이다.",
        "점수는 1.2.3대1이다.",
        "점수는 1/대2이다.",
        "점수는 1//2대3이다.",
        "점수는 2대1,00이다.",
        "점수는 2대1.2.3이다.",
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
        ("2대1abc", "2대1abc"),
        ("x=2대1", "x=2대1"),
    ],
)
def test_korean_da_score_pair_protected_contexts(
    src: str, expected: str
) -> None:
    assert _normalize(src) == expected
    assert "korean_da_score_pair" not in _claim_owners(src)
