from engine.span_engine.transform import transform


def test_decimal_numeric_delimited_uses_jjeom_canonical():
    cases = [
        ("3.5~8kg", "삼쩜오에서 팔 킬로그램"),
        ("3.5~8kg은", "삼쩜오에서 팔 킬로그램은"),
        ("3.5~8cm", "삼쩜오에서 팔 센티미터"),
        ("3.5~8cm의 폭", "삼쩜오에서 팔 센티미터의 폭"),
        ("0.5~1.2kg", "영쩜오에서 일쩜이 킬로그램"),
        ("1.2:2.3 비율", "일쩜이 대 이쩜삼 비율"),
        ("1.250:3.14 비율이다", "일쩜이오영 대 삼쩜일사 비율이다"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_signed_colon_semantic_pair_positive_contexts():
    cases = [
        ("-1.250:3.14 비율이다", "마이너스 일쩜이오영 대 삼쩜일사 비율이다"),
        ("-1:2 비율", "마이너스 일 대 이 비율"),
        ("1:-2 비율", "일 대 마이너스 이 비율"),
        ("-1:-2 비율", "마이너스 일 대 마이너스 이 비율"),
        ("-0.0:1 비율", "마이너스 영쩜영 대 일 비율"),
        ("1.2:-2.30 경기", "일쩜이 대 마이너스 이쩜삼영 경기"),
        ("-1,000.50:2 배율", "마이너스 천쩜오영 대 이 배율"),
        ("+1:2 비율", "플러스 일 대 이 비율"),
        ("1:+2 비율", "일 대 플러스 이 비율"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_signed_colon_semantic_pair_negative_contexts():
    positive = [
        ("-1.250:3.14", "마이너스 일쩜이오영 대 삼쩜일사"),
        ("요한복음 -1:2", "요한복음 마이너스 일 대 이"),
    ]
    for source, expected in positive:
        assert transform(source) == expected

    cases = [
        "영상 -1:23",
        "line -1:2",
        "/path/-1:2/log",
        "-01:2 비율",
        "-1.:2 비율",
        "-.5:2 비율",
        "-1,00.5:2 비율",
    ]
    for source in cases:
        assert transform(source) == source


def test_signed_tilde_like_unit_range_positive_contexts():
    cases = [
        ("-2.3~4.5kg이다", "마이너스 이쩜삼에서 사쩜오 킬로그램이다"),
        ("2.3~-4.5kg", "이쩜삼에서 마이너스 사쩜오 킬로그램"),
        ("-2.3~-4.5kg", "마이너스 이쩜삼에서 마이너스 사쩜오 킬로그램"),
        ("-2~4kg", "마이너스 이에서 사 킬로그램"),
        ("2~-4kg", "이에서 마이너스 사 킬로그램"),
        ("-2~-4kg", "마이너스 이에서 마이너스 사 킬로그램"),
        ("-0.0~1.5cm", "마이너스 영쩜영에서 일쩜오 센티미터"),
        ("-1,000.50~2,000.75원", "마이너스 천쩜오영에서 이천쩜칠오 원"),
        ("-2.3～4.5kg", "마이너스 이쩜삼에서 사쩜오 킬로그램"),
        ("-2.3∼4.5kg", "마이너스 이쩜삼에서 사쩜오 킬로그램"),
        ("-2.3〜4.5kg", "마이너스 이쩜삼에서 사쩜오 킬로그램"),
        ("+2.3~4.5kg", "플러스 이쩜삼에서 사쩜오 킬로그램"),
        ("2.3~+4.5kg", "이쩜삼에서 플러스 사쩜오 킬로그램"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_signed_tilde_like_unit_range_negative_contexts():
    for source in (
        "-2.3-4.5kg",
        "-2.3–4.5kg",
    ):
        out = transform(source)
        assert "에서" not in out
        assert out == source

    cases = [
        ("-2.3~4.5", "마이너스 이쩜삼에서 사쩜오"),
    ]
    for source, expected in cases:
        assert transform(source) == expected

    preserve_cases = [
        "-2.3~4.5alpha",
        "/path/-2.3~4.5kg/log",
        "`-2.3~4.5kg`",
        "-01.5~2kg",
        "-1.~2kg",
        "-.5~2kg",
        "-1,00.5~2kg",
    ]
    for source in preserve_cases:
        assert transform(source) == source
    assert transform("-2.3~4.5테스트") == "마이너스 이쩜삼에서 사쩜오 테스트"


def test_signed_tilde_range_preserves_existing_owner_precedence_and_neighbors():
    assert transform("10~20분") == "십분에서 이십분"
    assert transform("10∼20분") == "십분에서 이십분"
    assert transform("10〜20분") == "십분에서 이십분"
    assert transform("10～20분") == "십분에서 이십분"
    assert (
        transform("pH -2.3와 -2.3~4.5kg")
        == "피에이치 마이너스 이쩜삼와 마이너스 이쩜삼에서 사쩜오 킬로그램"
    )
    assert transform("v-2.3~4.5kg") == "v-2.3~4.5kg"
    assert (
        transform("`-1.250:3.14 비율` 옆 25℃")
        == "`-1.250:3.14 비율` 옆 이십오도"
    )
