from __future__ import annotations

import pytest

from engine.main import transform, transform_debug
from engine.span_engine.signed_numeric import (
    SIGNED_OWNER_POLICIES,
    SignKind,
    SignProfile,
    parse_signed_numeric_core,
    render_signed_numeric,
)


@pytest.mark.parametrize(
    ("raw", "sign_kind", "numeric_form", "integer_digits", "fractional_digits"),
    [
        ("+1", SignKind.PLUS, "INTEGER", "1", None),
        ("-0", SignKind.MINUS, "INTEGER", "0", None),
        ("+1.50", SignKind.PLUS, "DECIMAL", "1", "50"),
        ("-0.0", SignKind.MINUS, "DECIMAL", "0", "0"),
        ("+1,000", SignKind.PLUS, "COMMA_INTEGER", "1000", None),
        ("-1,000,000.0", SignKind.MINUS, "COMMA_DECIMAL", "1000000", "0"),
    ],
)
def test_common_signed_numeric_core_preserves_source_digits(
    raw: str,
    sign_kind: SignKind,
    numeric_form: str,
    integer_digits: str,
    fractional_digits: str | None,
) -> None:
    core = parse_signed_numeric_core(raw, require_sign=True)
    assert core is not None
    assert core.sign_kind is sign_kind
    assert core.sign_surface == raw[0]
    assert core.numeric_form == numeric_form
    assert core.integer_digits == integer_digits
    assert core.fractional_digits == fractional_digits


@pytest.mark.parametrize(
    "raw",
    [
        "+01",
        "-01",
        "+.5",
        "-.5",
        "+1.",
        "-1.",
        "++1",
        "--1",
        "+-1",
        "-+1",
        "+1,00",
        "-10,00",
        "+1,0000",
        "-1,00.5",
        "+ 1",
        "- 1",
    ],
)
def test_common_signed_numeric_core_rejects_invalid_full_surface(raw: str) -> None:
    assert parse_signed_numeric_core(raw, require_sign=True) is None


def test_default_and_temperature_sign_profiles_share_numeric_core() -> None:
    core = parse_signed_numeric_core("-1,000.50", require_sign=True)
    assert core is not None
    assert render_signed_numeric(core) == "마이너스 천쩜오영"
    assert (
        render_signed_numeric(core, sign_profile=SignProfile.TEMPERATURE)
        == "영하 천쩜오영"
    )


def test_owner_policy_does_not_expand_compound_unit_or_counter_signs() -> None:
    assert SIGNED_OWNER_POLICIES["compound_slash_unit"].sign_profile is SignProfile.UNSIGNED_ONLY
    assert SIGNED_OWNER_POLICIES["counter_noun"].sign_profile is SignProfile.UNSIGNED_ONLY
    assert (
        SIGNED_OWNER_POLICIES["ambiguous_numeric_dae_preserve"].sign_profile
        is SignProfile.UNSIGNED_ONLY
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+1", "플러스 일"),
        ("-1", "마이너스 일"),
        ("+25", "플러스 이십오"),
        ("-25", "마이너스 이십오"),
        ("+0", "플러스 영"),
        ("-0", "마이너스 영"),
        ("+1.50", "플러스 일쩜오영"),
        ("-0.0", "마이너스 영쩜영"),
        ("+1,000.50", "플러스 천쩜오영"),
        ("-12,345", "마이너스 만이천삼백사십오"),
        ("-1,000,000.0", "마이너스 백만쩜영"),
    ],
)
def test_standalone_signed_numeric_canonical(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("+1.5kg", "플러스 일쩜오 킬로그램", "simple_unit"),
        ("-45㎡", "마이너스 사십오 제곱미터", "special_unit"),
        ("+10%", "플러스 십 퍼센트", "simple_unit"),
        ("-2.5%p", "마이너스 이쩜오 퍼센트포인트", "percent_point"),
        ("+1,000원", "플러스 천 원", "currency"),
        ("-1,000.50원", "마이너스 천쩜오영 원", "currency"),
        ("+$10", "플러스 십 달러", "currency"),
        ("$-10", "마이너스 십 달러", "currency"),
        ("+25.50억", "플러스 이십오쩜오영 억", "large_unit_atomic"),
        ("-1/3", "마이너스 삼분의 일", "fraction"),
    ],
)
def test_structured_signed_owners_use_default_profile(
    text: str,
    expected: str,
    owner: str,
) -> None:
    assert transform(text) == expected
    debug = transform_debug(text)["debug"]
    parser_log = next(log for log in debug["trace"]["parser_logs"] if log["owner"] == owner)
    assert parser_log["metadata"]["sign_profile"] == "default"
    assert parser_log["metadata"]["sign_surface"] in {"+", "-"}


@pytest.mark.parametrize(
    ("text", "expected", "owner", "profile"),
    [
        ("+25℃", "영상 이십오도", "signed_temperature", "temperature"),
        ("-25°C", "영하 이십오도", "signed_temperature", "temperature"),
        ("+77°F", "화씨 영상 칠십칠도", "signed_temperature", "temperature"),
        ("-77°F", "화씨 영하 칠십칠도", "signed_temperature", "temperature"),
        ("+30°", "플러스 삼십도", "signed_degree", "default"),
        ("-30°", "마이너스 삼십도", "signed_degree", "default"),
        ("+30º", "영상 삼십도", "signed_degree", "temperature"),
        ("-30º", "영하 삼십도", "signed_degree", "temperature"),
    ],
)
def test_temperature_and_angle_sign_profiles(
    text: str,
    expected: str,
    owner: str,
    profile: str,
) -> None:
    assert transform(text) == expected
    parser_log = transform_debug(text)["debug"]["trace"]["parser_logs"][0]
    assert parser_log["owner"] == owner
    assert parser_log["metadata"]["sign_profile"] == profile


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("+1:2", "플러스 일 대 이", "colon_semantic_pair"),
        ("1:-2", "일 대 마이너스 이", "colon_semantic_pair"),
        ("+1.5:-2.0", "플러스 일쩜오 대 마이너스 이쩜영", "colon_semantic_pair"),
        ("+2.3~4kg", "플러스 이쩜삼에서 사 킬로그램", "range_with_unit"),
        ("2.3~-4.5kg", "이쩜삼에서 마이너스 사쩜오 킬로그램", "range_with_unit"),
        ("+82-10-1234-5678", "플러스 팔이 일공 일이삼사 오육칠팔", "phone"),
    ],
)
def test_existing_structured_signed_owner_output_and_owner_are_unchanged(
    text: str,
    expected: str,
    owner: str,
) -> None:
    assert transform(text) == expected
    claim = transform_debug(text)["debug"]["trace"]["claim_logs"][0]
    assert claim["owner"] == owner
    assert claim["span"] == {"start": 0, "end": len(text), "length": len(text)}


def test_international_phone_with_korean_tail_is_not_blocked_by_invalid_preserve() -> None:
    text = "+1-800-123-4567로"
    assert transform(text) == "플러스 일 팔공공 일이삼 사오육칠로"
    claims = transform_debug(text)["debug"]["trace"]["claim_logs"]
    assert claims[0]["owner"] == "phone"
    assert claims[0]["span"] == {"start": 0, "end": 15, "length": 15}


@pytest.mark.parametrize(
    "text",
    [
        "+01",
        "-01",
        "+.5",
        "-.5",
        "+1.",
        "-1.",
        "++1",
        "--1",
        "-+1",
        "+1,00",
        "-1,0000",
    ],
)
def test_invalid_signed_surface_is_atomically_preserved(text: str) -> None:
    assert transform(text) == text
    debug = transform_debug(text)["debug"]
    assert debug["trace"]["claim_logs"] == [
        {
            "claim_type": "preserve",
            "owner": "preserve",
            "reason": "invalid_or_unsupported_signed_numeric_surface_preserve",
            "reentry_allowed": False,
            "span": {"start": 0, "end": len(text), "length": len(text)},
            "surface_type": "INVALID_OR_UNSUPPORTED_SIGNED_NUMERIC_PRESERVE_SURFACE",
        }
    ]
    assert all(
        piece["provenance"] != "GENERATED_READING"
        for piece in debug["render_pieces"]
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3대", "플러스 삼 대"),
        ("-3대", "마이너스 삼 대"),
        ("차량 증감 +3대", "차량 증감 플러스 삼 대"),
        ("+2명", "플러스 이 명"),
        ("-3개", "마이너스 삼 개"),
    ],
)
def test_signed_counter_and_dae_use_residual_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["+10km/h", "-3m/s"])
def test_signed_compound_slash_unit_support_is_not_expanded(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "C++17",
        "A+B",
        "x-y=3",
        "a+=1",
        "email+tag@example.com",
        "https://example.com?q=+1",
        "/path/-1/log",
        '{"value":"+1"}',
        "`-2.5kg`",
    ],
)
def test_protected_or_code_like_context_does_not_reenter_signed_owner(text: str) -> None:
    assert transform(text) == text
    claims = transform_debug(text)["debug"]["trace"]["claim_logs"]
    assert not any(claim["owner"].startswith("signed_") for claim in claims)


def test_mixed_signed_numeric_e2e() -> None:
    text = (
        "값은 +1,000.50원, 변화율은 -2.5%p, 무게는 +1.5kg, 온도는 -25℃, "
        "각도는 +30°, 경기는 +1:-2였고 차량 변화 +3대는 원문으로 기록했다."
    )
    expected = (
        "값은 플러스 천쩜오영 원, 변화율은 마이너스 이쩜오 퍼센트포인트, "
        "무게는 플러스 일쩜오 킬로그램, 온도는 영하 이십오도, 각도는 플러스 삼십도, "
            "경기는 플러스 일 대 마이너스 이였고 차량 변화 플러스 삼 대는 원문으로 기록했다."
    )
    assert transform(text) == expected
