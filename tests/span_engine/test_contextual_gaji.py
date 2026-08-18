from __future__ import annotations

import pytest

from engine.main import transform, transform_debug


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0가지", "영 가지"),
        ("1가지", "한 가지"),
        ("2가지", "두 가지"),
        ("3가지", "세 가지"),
        ("4가지", "네 가지"),
        ("10가지", "열 가지"),
        ("20가지", "스무 가지"),
        ("21가지", "스물한 가지"),
        ("39가지", "서른아홉 가지"),
        ("40가지", "마흔 가지"),
        ("99가지", "아흔아홉 가지"),
        ("100가지", "백 가지"),
        ("101가지", "백일 가지"),
        ("4 가지", "네 가지"),
    ],
)
def test_gaji_uses_canonical_native_count_reading(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4가지가", "네 가지가"),
        ("4가지를", "네 가지를"),
        ("4가지로", "네 가지로"),
        ("4가지만", "네 가지만"),
        ("4가지입니다", "네 가지입니다"),
        ("문제에는 3가지 원인과 4가지 해결책이 있습니다.", "문제에는 세 가지 원인과 네 가지 해결책이 있습니다."),
        ("네 가지 방법", "네 가지 방법"),
        ("여러 가지 방법", "여러 가지 방법"),
        ("몇 가지 방법", "몇 가지 방법"),
    ],
)
def test_gaji_particles_multiple_surfaces_and_hangul_preserve(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "01가지",
        "1,00가지",
        "4A가지",
    ],
)
def test_gaji_malformed_surface_is_deferred_atomically(text: str) -> None:
    debug = transform_debug(text)
    assert debug["normalized_text"] == text
    claims = debug["debug"]["trace"]["claim_logs"]
    assert len(claims) == 1
    assert claims[0]["owner"] == "contextual_number_unit"
    assert claims[0]["claim_type"] == "preserve"
    assert not any(
        claim["owner"]
        in {"number", "signed_number", "decimal", "numeric_suffix", "counter_noun"}
        for claim in claims
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+4가지", "플러스 사 가지"),
        ("-4가지", "마이너스 사 가지"),
    ],
)
def test_gaji_signed_surfaces_use_residual_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_gaji_prefixed_ordinal_uses_attached_sino_reading() -> None:
    debug = transform_debug("제4가지")
    assert debug["normalized_text"] == "제 사가지"
    claims = debug["debug"]["trace"]["claim_logs"]
    assert any(claim["owner"] == "numeric_suffix" for claim in claims)


def test_gaji_valid_decimal_uses_sino_decimal_reading() -> None:
    debug = transform_debug("1.5가지")
    assert debug["normalized_text"] == "일쩜오 가지"
    assert debug["debug"]["trace"]["contextual_decision_logs"][0][
        "decision"
    ] == "confirmed"


def test_gaji_range_owner_keeps_precedence_and_native_endpoints() -> None:
    debug = transform_debug("3~4가지")
    assert debug["normalized_text"] == "세 가지에서 네 가지"
    claims = debug["debug"]["trace"]["claim_logs"]
    assert [claim["owner"] for claim in claims] == ["range"]


@pytest.mark.parametrize(
    "text",
    [
        "`4가지`",
        "/path/4가지/file",
        '{"value":"4가지"}',
        "item_4가지",
        "4가지.json",
        "https://example.com/4가지",
    ],
)
def test_gaji_protected_surfaces_are_unchanged(text: str) -> None:
    assert transform(text) == text
    logs = transform_debug(text)["debug"]["trace"]["contextual_decision_logs"]
    assert logs == []


def test_gaji_debug_decision_and_provenance_are_debug_only() -> None:
    debug = transform_debug("4가지를")
    assert debug["normalized_text"] == "네 가지를"
    logs = debug["debug"]["trace"]["contextual_decision_logs"]
    assert len(logs) == 1
    assert logs[0]["unit"] == "가지"
    assert logs[0]["decision"] == "confirmed"
    assert logs[0]["semantic_type"] == "kind_or_item_count"
    assert logs[0]["confirmed_reading"] == "네 가지를"
    assert logs[0]["existing_engine_result"] == "사가지를"
    assert logs[0]["new_rule_result"] == "네 가지를"
    assert logs[0]["source_span"] == {"start": 0, "end": 4, "length": 4}
    assert logs[0]["actual_final_output"] == "네 가지를"
    assert "contextual_decision" not in transform("4가지를")

    pieces = debug["debug"]["render_pieces"]
    assert [(piece["text"], piece["provenance"]) for piece in pieces] == [
        ("네", "GENERATED_READING"),
        (" ", "GENERATED_READING"),
        ("가지를", "ORIGINAL_KOREAN"),
    ]
