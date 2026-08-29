from engine.span_engine.delimiters import (
    COLON_LIKE_DELIMITERS,
    RANGE_LIKE_DELIMITERS,
    is_colon_like,
    is_range_like,
)
from engine.span_engine.transform import transform


def test_shared_delimiter_classes_first_pass_sets():
    assert COLON_LIKE_DELIMITERS == {":", "："}
    assert RANGE_LIKE_DELIMITERS == {"-", "–", "~", "～"}
    assert is_colon_like(":")
    assert is_colon_like("：")
    assert not is_colon_like("∶")
    assert is_range_like("-")
    assert is_range_like("–")
    assert is_range_like("~")
    assert is_range_like("～")
    assert not is_range_like("〜")
    assert not is_range_like("−")
    assert not is_range_like("—")


def test_colon_like_delimiter_equivalence_for_time_semantic_pair_and_fallback():
    cases = [
        ("1：2 비율", "일 대 이 비율"),
        ("1：2테스트", "일 대 이 테스트"),
        ("1.5：2 비율", "일쩜오 대 이 비율"),
        ("1.5：2범위", "일쩜오 대 이 범위"),
        ("1：2：3", "일 대 이 대 삼"),
        ("1:2：3", "일 대 이 대 삼"),
        ("2：0으로 이겼다", "이 대 영으로 이겼다"),
        ("13：05에 시작", "십삼시 오분에 시작"),
        ("13：05", "십삼시 오분"),
        ("1：2", "일 대 이"),
        ("요한복음 3：16", "요한복음 3：16"),
        ("영상 1：23", "영상 1：23"),
        ("`1：2 비율`", "`1：2 비율`"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_range_like_delimiter_equivalence_for_unit_ranges_and_fallback():
    cases = [
        ("1–2개", "일에서 이-개"),
        ("1~2개", "일에서 이-개"),
        ("1～2개", "일에서 이-개"),
        ("1–2kg", "일에서 이-킬로그램"),
        ("1.5–2kg", "일쩜오에서 이-킬로그램"),
        ("1.5~2kg", "일쩜오에서 이-킬로그램"),
        ("1.5～2kg", "일쩜오에서 이-킬로그램"),
        ("1~2cm", "일에서 이-센티미터"),
        ("1–2테스트", "1–2테스트"),
        ("1~2테스트", "일에서 이 테스트"),
        ("1～2테스트", "일에서 이 테스트"),
        ("/path/1–2/log", "/path/1–2/log"),
        ("`1~2개`", "`1~2개`"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_delimiter_equivalence_is_scanner_local_with_neighbor_survival():
    cases = [
        ("1:2 비율과 25℃, $25.99, 3kg", "일 대 이 비율"),
        ("1：2 비율과 25℃, $25.99, 3kg", "일 대 이 비율"),
    ]
    for source, semantic_pair in cases:
        out = transform(source)
        assert semantic_pair in out
        assert "이십오도" in out
        assert "이십오쩜구구-달러" in out
        assert "삼-킬로그램" in out
