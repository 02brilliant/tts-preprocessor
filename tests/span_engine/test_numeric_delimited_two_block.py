from engine.span_engine.transform import transform
from engine.span_engine.range import hyphen_range_compatible_korean_suffix_reading
from engine.span_engine.units import range_compatible_unit_reading


def test_hyphen_range_compatibility_metadata_helpers():
    assert range_compatible_unit_reading("kg") == "킬로그램"
    assert range_compatible_unit_reading("%") == "퍼센트"
    assert range_compatible_unit_reading("mph") is None
    assert hyphen_range_compatible_korean_suffix_reading("장") == "장"
    assert hyphen_range_compatible_korean_suffix_reading("페이지") == "페이지"
    assert hyphen_range_compatible_korean_suffix_reading("테스트") is None


def test_hyphen_two_block_standalone_blocks_internal_numeric_fallback():
    for source in ("1–2", "12-31", "123-456"):
        assert transform(source) == source


def test_ascii_hyphen_two_block_is_ambiguous_preserve():
    assert transform("1-2") == "1-2"


def test_leading_zero_two_block_uses_digit_code_reading():
    assert transform("03-04") == "공삼 공사"


def test_hyphen_two_block_with_range_compatible_unit():
    cases = [
        ("1-2장", "일에서 이-장"),
        ("1–2장", "일에서 이-장"),
        ("1~2장", "일에서 이-장"),
        ("1～2장", "일에서 이-장"),
        ("3-4페이지", "삼에서 사-페이지"),
        ("10-20개", "십에서 이십-개"),
        ("10–20개", "십에서 이십-개"),
        ("2-3명", "이에서 삼-명"),
        ("3-5분", "삼에서 오-분"),
        ("1-2kg", "일에서 이-킬로그램"),
        ("1–2kg", "일에서 이-킬로그램"),
        ("1~2kg", "일에서 이-킬로그램"),
        ("1～2kg", "일에서 이-킬로그램"),
        ("2-3cm", "이에서 삼-센티미터"),
        ("10-20%", "십에서 이십-퍼센트"),
        ("100-200원", "백에서 이백-원"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_hyphen_two_block_optional_spacing_and_korean_tail():
    cases = [
        ("1-2 장", "일에서 이-장"),
        ("1-2 장입니다", "일에서 이-장입니다"),
        ("1-2장으로", "일에서 이-장으로"),
        ("10-20 개는", "십에서 이십-개는"),
        ("10-20개는", "십에서 이십-개는"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_hyphen_two_block_non_unit_and_code_like_contexts_preserve():
    cases = [
        "1-2테스트",
        "1–2테스트",
        "1-2버그",
        "1-2alpha",
        "1-2mph",
        "v1-2",
        "/path/1-2/log",
        "/path/1–2/log",
        "`1-2`",
        "`1~2개`",
    ]
    for source in cases:
        assert transform(source) == source
    assert transform("1~2테스트") == "일에서 이 테스트"
    assert transform("1～2테스트") == "일에서 이 테스트"


def test_hyphen_two_block_range_preserves_input_order_without_value_gate():
    assert transform("5-3개") == "오에서 삼-개"


def test_hyphen_two_block_arbitrary_noun_does_not_range_claim():
    out = transform("1-2케이스ID")
    assert "1-2케이스" in out
    assert "일에서 이 케이스" not in out


def test_colon_two_block_standalone_blocks_internal_numeric_fallback():
    for source in ("9:30", "3:15", "10:20"):
        assert transform(source) == source
    assert transform("13:05") == "십삼시 오분"
    assert transform("13：05") == "십삼시 오분"
    assert transform("1:2") == "일 대 이"
    assert transform("1：2") == "일 대 이"


def test_colon_two_block_time_requires_explicit_context():
    cases = [
        ("13:05에 시작", "십삼시 오분에 시작"),
        ("13：05에 시작", "십삼시 오분에 시작"),
        ("14:00부터", "십사시부터"),
        ("18:30까지", "십팔시 삼십분까지"),
        ("오전 9:30", "오전 아홉시 삼십분"),
        ("오후 3:15", "오후 세시 십오분"),
        ("AM 10:20", "AM 열시 이십분"),
        ("PM 8:05", "PM 여덟시 오분"),
        ("회의 14:00", "회의 십사시"),
        ("마감 18:00", "마감 십팔시"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_two_block_semantic_pair_contexts_transform():
    cases = [
        ("2:0으로 이겼다", "이 대 영으로 이겼다"),
        ("3:1 승리", "삼 대 일 승리"),
        ("1:2 비율", "일 대 이 비율"),
        ("1：2 비율", "일 대 이 비율"),
        ("16:9 화면비", "십육 대 구 화면비"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_two_block_non_semantic_ambiguous_contexts_preserve():
    for source in ("요한복음 3:16", "요한복음 3：16", "line 10:20"):
        assert transform(source) == source


def test_colon_two_block_duration_media_contexts_are_not_time():
    cases = [
        "영상 1:23",
        "영상 1：23",
        "재생시간 03:15",
        "타임라인 00:03",
    ]
    for source in cases:
        assert transform(source) == source


def test_invalid_time_like_surface_preserves_with_explicit_context():
    assert transform("13:99") == "십삼 대 구십구"
    assert transform("24:01부터") == "이십사시 일분부터"
    cases = [
        "13:99에 시작",
        "오전 13:05",
    ]
    for source in cases:
        assert transform(source) == source


def test_protected_numeric_delimited_spans_do_not_block_neighbors():
    text = "`1-2` 옆 25℃와 3kg은 처리해야 합니다."
    out = transform(text)
    assert out != text
    assert "`1-2`" in out
    assert "이십오도" in out
    assert "삼-킬로그램" in out

    text = (
        '"The meeting was at 13:05."라고 적었고, '
        "밖의 $25.99와 pH 7.4는 처리해야 합니다."
    )
    out = transform(text)
    assert out != text
    assert "The meeting was at 13:05." in out
    assert "이십오쩜구구-달러" in out
    assert "피에이치 칠쩜사" in out
