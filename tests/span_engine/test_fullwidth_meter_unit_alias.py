from __future__ import annotations

import pytest

from engine.main import transform as canonical_transform
from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1ｍ", "일 미터"),
        ("지름 약 1ｍ입니다.", "지름 약 일 미터입니다."),
        ("1~2ｍ", "일에서 이 미터"),
        ("깊이 약 1~2ｍ로 파악됐습니다.", "깊이 약 일에서 이 미터로 파악됐습니다."),
        (
            "경찰과 소방 당국에 따르면 땅꺼짐 규모는 지름 약 1ｍ, 깊이 약 1~2ｍ로 파악됐습니다.",
            "경찰과 소방 당국에 따르면 땅꺼짐 규모는 지름 약 일 미터, 깊이 약 일에서 이 미터로 파악됐습니다.",
        ),
    ],
)
def test_fullwidth_meter_unit_alias_positive_production(text: str, expected: str) -> None:
    assert canonical_transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1m", "일 미터"),
        ("1~2m", "일에서 이 미터"),
        ("1cm", "일 센티미터"),
        ("1~2cm", "일에서 이 센티미터"),
        ("1㎝", "일 센티미터"),
        ("1㎏", "일 킬로그램"),
    ],
)
def test_fullwidth_meter_alias_preserves_existing_unit_outputs(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "+.5ｍ",
        "1,00ｍ",
        "1~~2ｍ",
        "1ｍabc",
        "1ｍ/s",
        "/path/1ｍ/log",
        "https://example.com?q=1ｍ",
        '{"depth":"1ｍ"}',
        "`1ｍ`",
        "ＡＩ",
        "ＫＴＸ",
    ],
)
def test_fullwidth_meter_alias_preserve_and_no_broad_fullwidth_normalization(
    text: str,
) -> None:
    assert transform(text) == text


def test_fullwidth_meter_alias_square_bracket_preserve_then_unwrap() -> None:
    assert transform("[1ｍ]") == "1ｍ"


def test_fullwidth_meter_alias_claim_owners() -> None:
    unit_output = transform_with_trace("1ｍ")
    range_output = transform_with_trace("1~2ｍ로")

    assert unit_output.normalized_text == "일 미터"
    assert any(claim.owner == "simple_unit" for claim in unit_output.trace.claim_logs)
    assert not any(claim.owner == "number" for claim in unit_output.trace.claim_logs)

    assert range_output.normalized_text == "일에서 이 미터로"
    assert any(claim.owner == "range_with_unit" for claim in range_output.trace.claim_logs)
    assert not any(claim.owner == "number" for claim in range_output.trace.claim_logs)
