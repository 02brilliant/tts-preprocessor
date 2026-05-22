from engine.span_engine.transform import transform


def test_three_block_multi_colon_numeric_positive_contexts():
    cases = [
        ("1:2:3", "일 대 이 대 삼"),
        ("1.2:2.3:3.4", "일쩜이 대 이쩜삼 대 삼쩜사"),
        ("-1:2:-3", "마이너스 일 대 이 대 마이너스 삼"),
        ("1,000:2,000:3,000", "천 대 이천 대 삼천"),
        ("1.250:2.00:3.5", "일쩜이오영 대 이쩜영영 대 삼쩜오"),
        ("1：2：3", "일 대 이 대 삼"),
        ("1:2：3", "일 대 이 대 삼"),
        ("+1:2:3", "플러스 일 대 이 대 삼"),
        ("+1.2:2.3:+3.0", "플러스 일쩜이 대 이쩜삼 대 플러스 삼쩜영"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_three_block_multi_colon_timecode_like_preserves():
    cases = [
        "1:02:03",
        "01:02:03",
        "23:59:59",
        "1:02:03.5",
        "01:02:03.250",
        "오전 1:02:03",
        "영상 1:02:03",
        "1:02:03 비율",
        "+1:02:03",
    ]
    for source in cases:
        assert transform(source) == source


def test_four_to_eight_block_multi_colon_numeric_positive_contexts():
    cases = [
        ("1:2:3:4", "일 대 이 대 삼 대 사"),
        ("1:2:3:4:5", "일 대 이 대 삼 대 사 대 오"),
        (
            "1:2:3:4:5:6:7:8",
            "일 대 이 대 삼 대 사 대 오 대 육 대 칠 대 팔",
        ),
        (
            "-1.2:2.3:-3:4",
            "마이너스 일쩜이 대 이쩜삼 대 마이너스 삼 대 사",
        ),
        (
            "1:+2:-3:4",
            "일 대 플러스 이 대 마이너스 삼 대 사",
        ),
        (
            "1,000:2,000:3,000:4,000",
            "천 대 이천 대 삼천 대 사천",
        ),
        (
            "1.250:2.00:3.5:4",
            "일쩜이오영 대 이쩜영영 대 삼쩜오 대 사",
        ),
        ("1：2：3：4", "일 대 이 대 삼 대 사"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_multi_colon_max_blocks_and_invalid_blocks_preserve():
    cases = [
        "1:2:3:4:5:6:7:8:9",
        "1:2:3:4:5:6:7:8:9:10",
        "01:2:3",
        "1:2.:3",
        "1:.2:3",
        "1,00:2:3",
        "-01:2:3",
        "1:2:03:4",
        "+01:2:3",
        "1:+2.:3",
        "1:+2:+3:+4:+5:+6:+7:+8:+9",
        "1::3",
    ]
    for source in cases:
        assert transform(source) == source


def test_multi_colon_protected_code_like_and_contexts_preserve():
    cases = [
        "/path/1:2:3/log",
        "/path/1:2:3:4/log",
        "`1:2:3`",
        "`1:2:3:4`",
        "version 1:2:3",
        "version 1:2:3:4",
        "line 10:20:30",
        "line 10:20:30:40",
        '{"ratio":"1:2:3"}',
        "요한복음 1:2:3",
    ]
    for source in cases:
        assert transform(source) == source


def test_multi_colon_regression_with_existing_owners():
    cases = [
        ("1:2 비율", "일 대 이 비율"),
        (
            "-1.250:3.14 비율이다",
            "마이너스 일쩜이오영 대 삼쩜일사 비율이다",
        ),
        ("13:05에 시작", "십삼시 오분에 시작"),
        ("1:02:03", "1:02:03"),
        ("3.5~8kg", "삼쩜오에서 팔 킬로그램"),
        ("-2.3~4.5kg", "마이너스 이쩜삼에서 사쩜오 킬로그램"),
        ("pH 7.4와 1:2:3", "피에이치 칠쩜사와 일 대 이 대 삼"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_multi_colon_invalid_surfaces_block_partial_numeric_fallback_with_neighbors():
    cases = [
        "1:02:03",
        "1:2:3:4:5:6:7:8:9",
        "-1.2:3:4:5:6:7:8:9:10",
        "01:2:3",
        "+01:2:3",
    ]
    for source in cases:
        text = f"{source} 옆 25℃"
        out = transform(text)
        assert source in out
        assert "이십오도" in out
