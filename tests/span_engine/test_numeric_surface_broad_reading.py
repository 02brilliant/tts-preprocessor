from __future__ import annotations

from engine.span_engine.transform import transform


INTEGRATED_SOURCE = (
    "오늘 실험실 온도는 +25℃였고, 아침에는 -3℃였지만, 문장 끝에는 +1.5kg. "
    "문장 끝에는 +3.140℃. 문장 끝 숫자 3.140. 문장끝 숫자 5. "
    "단독 +1:2와 3:4는 문맥이 없어도, 시간이 아니면 읽어야 한다. "
    "입력값 +1.5~2 구간과 3.410~3.56범위, 음수 입력인 -2.480~3.24까지 읽어야 한다. "
    "-2.480~3.24 이건 못읽는데, -2.480~+3.24 이건 읽는다."
)

INTEGRATED_EXPECTED = (
    "오늘 실험실 온도는 영상 이십오도였고, 아침에는 영하 삼도였지만, 문장 끝에는 플러스 일쩜오-킬로그램. "
    "문장 끝에는 영상 삼쩜일사영도. 문장 끝 숫자 삼쩜일사영. 문장끝 숫자 오. "
    "단독 플러스 일 대 이와 삼 대 사는 문맥이 없어도, 시간이 아니면 읽어야 한다. "
    "입력값 플러스 일쩜오에서 이 구간과 삼쩜사일영에서 삼쩜오육 범위, 음수 입력인 마이너스 이쩜사팔영에서 삼쩜이사까지 읽어야 한다. "
    "마이너스 이쩜사팔영에서 삼쩜이사 이건 못읽는데, 마이너스 이쩜사팔영에서 플러스 삼쩜이사 이건 읽는다."
)


def test_numeric_surface_broad_reading_integrated_sentence() -> None:
    assert transform(INTEGRATED_SOURCE) == INTEGRATED_EXPECTED


def test_signed_temperature_unit_percent_decimal_tail_boundaries() -> None:
    cases = [
        ("+25℃였고", "영상 이십오도였고"),
        ("-3℃였지만", "영하 삼도였지만"),
        ("+1.5kg.", "플러스 일쩜오-킬로그램."),
        ("+3.140℃.", "영상 삼쩜일사영도."),
        ("3.140.", "삼쩜일사영."),
        ("5.", "오."),
        ("+25%.", "플러스 이십오-퍼센트."),
        ("+1,000.50원.", "플러스 천쩜오영-원."),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_two_block_colon_broad_reading_and_time_like_guard() -> None:
    cases = [
        ("+1:2", "플러스 일 대 이"),
        ("3:4", "삼 대 사"),
        ("1.5:2.0", "일쩜오 대 이쩜영"),
        ("-1:+2", "마이너스 일 대 플러스 이"),
        ("1,000:2,000", "천 대 이천"),
        ("13:5", "십삼 대 오"),
        ("25:30", "이십오 대 삼십"),
        ("09:30", "아홉시 삼십분"),
        ("08:05", "여덟시 오분"),
        ("00:30", "영시 삼십분"),
        ("24:00", "이십사시"),
        ("24:09", "이십사시 구분"),
        ("09:30에 시작", "아홉시 삼십분에 시작"),
        ("13:05에 시작", "십삼시 오분에 시작"),
        ("24:09까지", "이십사시 구분까지"),
        ("24:09부터", "이십사시 구분부터"),
        ("+1:02", "+1:02"),
        ("+1:2", "플러스 일 대 이"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_tilde_numeric_range_broad_reading() -> None:
    cases = [
        ("1~2", "일에서 이"),
        ("+1.5~2", "플러스 일쩜오에서 이"),
        ("+1.5~2 구간", "플러스 일쩜오에서 이 구간"),
        ("3.410~3.56범위", "삼쩜사일영에서 삼쩜오육 범위"),
        ("-2.480~3.24", "마이너스 이쩜사팔영에서 삼쩜이사"),
        ("-2.480~+3.24", "마이너스 이쩜사팔영에서 플러스 삼쩜이사"),
        ("+2.480~-3.24", "플러스 이쩜사팔영에서 마이너스 삼쩜이사"),
        ("0.05~0.10cm", "영쩜영오에서 영쩜일영-센티미터"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_numeric_surface_broad_reading_invalid_and_protected_preserve() -> None:
    for source in (
        "+01:2",
        "+1.:2",
        "+.5:2",
        "+01.5~2",
        "+1,00.5~2",
        "+.5~2",
        "3..140~4",
        "`+1:2`",
        "`-2.480~3.24`",
        "/path/+1:2/log",
        "/path/-2.480~3.24/log",
        "https://example.com?q=+1:2",
        "email+tag@example.com",
        "-2.480-3.24",
    ):
        assert transform(source) == source
