from engine.span_engine.range import (
    parse_numeric_delimited_number,
    render_numeric_delimited_number,
)
from engine.span_engine.transform import transform


def test_numeric_delimited_decimal_rendering_preserves_fractional_digits():
    cases = [
        ("1.0", "일쩜영"),
        ("1.50", "일쩜오영"),
        ("1.500", "일쩜오영영"),
        ("0.05", "영쩜영오"),
        ("2.000", "이쩜영영영"),
        ("1,000.5", "천쩜오"),
        ("1,000,000.000", "백만쩜영영영"),
    ]
    for source, expected in cases:
        parsed = parse_numeric_delimited_number(source)
        assert parsed is not None
        assert render_numeric_delimited_number(parsed) == expected


def test_colon_decimal_semantic_pair_positive_contexts():
    cases = [
        ("1.5:2 비율", "일쩜오 대 이 비율"),
        ("1.5:2.0 비율", "일쩜오 대 이쩜영 비율"),
        ("0.5:1 희석", "영쩜오 대 일 희석"),
        ("1.25:100 축척", "일쩜이오 대 백 축척"),
        ("1,000.5:2 비율", "천쩜오 대 이 비율"),
        ("1:1,000,000.000 축척", "일 대 백만쩜영영영 축척"),
        ("2.0:0.0 무승부", "이쩜영 대 영쩜영 무승부"),
        ("3.50:1.25 경기", "삼쩜오영 대 일쩜이오 경기"),
        ("+1.5:2 비율", "플러스 일쩜오 대 이 비율"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_decimal_semantic_pair_negative_contexts():
    positive = [
        ("1.5:2", "일쩜오 대 이"),
        ("1.5:2 영상", "일쩜오 대 이 영상"),
        ("요한복음 3.5:16", "요한복음 삼쩜오 대 십육"),
    ]
    for source, expected in positive:
        assert transform(source) == expected

    cases = [
        "line 10.5:20",
        "01.5:2 비율",
        "1.:2 비율",
        ".5:2 비율",
        "1.5.2:2 비율",
        "1,00.5:2 비율",
    ]
    for source in cases:
        assert transform(source) == source


def test_hyphen_decimal_unit_range_positive_contexts():
    cases = [
        ("1.5-2kg", "일쩜오에서 이 킬로그램"),
        ("0.5-1.0cm", "영쩜오에서 일쩜영 센티미터"),
        ("1,000.5-2,000.75원", "천쩜오에서 이천쩜칠오 원"),
        ("2.0-1.5kg", "이쩜영에서 일쩜오 킬로그램"),
        ("1.50-2.00kg", "일쩜오영에서 이쩜영영 킬로그램"),
        ("0.05-0.10cm", "영쩜영오에서 영쩜일영 센티미터"),
        ("1.25~2.5kg", "일쩜이오에서 이쩜오 킬로그램"),
        ("1.25–2.5kg", "일쩜이오에서 이쩜오 킬로그램"),
        ("1.25～2.5kg", "일쩜이오에서 이쩜오 킬로그램"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_hyphen_decimal_unit_range_negative_contexts():
    cases = [
        "1.5-2",
        "1.5-2테스트",
        "1.5-2alpha",
        "v1.5-2",
        "/path/1.5-2kg/log",
        "`1.5-2kg`",
        "01.5-2kg",
        "1.-2kg",
        ".5-2kg",
        "1,00.5-2kg",
        "-1.5-2kg",
    ]
    for source in cases:
        assert transform(source) == source


def test_decimal_delimiter_equivalence():
    cases = [
        ("1.5：2 비율", "일쩜오 대 이 비율"),
        ("1：2.0 비율", "일 대 이쩜영 비율"),
        ("1.5：2", "일쩜오 대 이"),
        ("1.5–2kg", "일쩜오에서 이 킬로그램"),
        ("1.5~2kg", "일쩜오에서 이 킬로그램"),
        ("1.5～2kg", "일쩜오에서 이 킬로그램"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_decimal_delimited_protected_code_like_and_neighbors():
    cases = [
        ("`1.5:2 비율` 옆 25℃", "`1.5:2 비율` 옆 이십오도"),
        ("`1.5-2kg` 옆 $25.99", "`1.5-2kg` 옆 이십오쩜구구 달러"),
        ("pH 7.4와 1.5-2kg", "피에이치 칠쩜사와 일쩜오에서 이 킬로그램"),
        ("v1.5-2와 1.5-2kg", "v1.5-2와 일쩜오에서 이 킬로그램"),
        ("/path/1.5:2/log", "/path/1.5:2/log"),
    ]
    for source, expected in cases:
        assert transform(source) == expected
