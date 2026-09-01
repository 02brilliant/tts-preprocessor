from __future__ import annotations

from engine.span_engine.transform import transform


def test_fahrenheit_label_symbol_context_deduplicates() -> None:
    cases = [
        ("화씨 +77°F", "화씨 영상 칠십칠도"),
        ("화씨 -77°F", "화씨 영하 칠십칠도"),
        ("화씨 +77℉", "화씨 영상 칠십칠도"),
        ("화씨 -77℉", "화씨 영하 칠십칠도"),
        ('화씨 +1.5°F', '화씨 영상 일-쩜-오도'),
        ('화씨 -0.0°F', '화씨 영하 영-쩜-영도'),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_celsius_label_symbol_context_deduplicates() -> None:
    cases = [
        ("섭씨 +25°C", "섭씨 영상 이십오도"),
        ("섭씨 -25°C", "섭씨 영하 이십오도"),
        ("섭씨 +25℃", "섭씨 영상 이십오도"),
        ("섭씨 -25℃", "섭씨 영하 이십오도"),
        ('섭씨 +1.5°C', '섭씨 영상 일-쩜-오도'),
        ('섭씨 -0.0°C', '섭씨 영하 영-쩜-영도'),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_standalone_temperature_canonical_is_unchanged() -> None:
    cases = [
        ("+77°F", "화씨 영상 칠십칠도"),
        ("-77°F", "화씨 영하 칠십칠도"),
        ("+77℉", "화씨 영상 칠십칠도"),
        ("-77℉", "화씨 영하 칠십칠도"),
        ("+25℃", "영상 이십오도"),
        ("-25℃", "영하 이십오도"),
        ("+25°C", "영상 이십오도"),
        ("-25°C", "영하 이십오도"),
        ("오늘 +77°F였다", "오늘 화씨 영상 칠십칠도였다"),
        ("오늘 -77°F였다", "오늘 화씨 영하 칠십칠도였다"),
        ("오늘 +77℉였다", "오늘 화씨 영상 칠십칠도였다"),
        ("오늘 -77℉였다", "오늘 화씨 영하 칠십칠도였다"),
        ("오늘 +25℃였다", "오늘 영상 이십오도였다"),
        ("오늘 -25℃였다", "오늘 영하 이십오도였다"),
        ("오늘 +25°C였다", "오늘 영상 이십오도였다"),
        ("오늘 -25°C였다", "오늘 영하 이십오도였다"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_temperature_label_symbol_mismatch_keeps_current_behavior() -> None:
    assert transform("섭씨 +77°F") == "섭씨 화씨 영상 칠십칠도"
    assert transform("화씨 +25°C") == "화씨 영상 이십오도"


def test_temperature_context_deduplication_respects_protected_contexts() -> None:
    for source in (
        "`화씨 +77°F`",
        "/path/화씨+77°F/log",
        '{"temp":"화씨 +77°F"}',
    ):
        assert transform(source) == source


def test_temperature_context_deduplication_long_sentence_regressions() -> None:
    text = (
        "보고서에는 화씨 +77°F, 섭씨 -3℃, 전화번호 +82-10-1234-5678, "
        "화면비 16:9 화면비, multi-colon 값 1:2:3:4:5:6:7:8, "
        "그리고 초과 블럭 1:2:3:4:5:6:7:8:9가 함께 포함되어 있다."
    )
    output = transform(text)
    assert "화씨 영상 칠십칠도" in output
    assert "화씨 화씨 영상" not in output
    assert "섭씨 영하 삼도" in output
    assert "플러스 팔이 일공 일이삼사 오육칠팔" in output
    assert "십육 대 구 화면비" in output
    assert "일 대 이 대 삼 대 사 대 오 대 육 대 칠 대 팔" in output
    assert "1:2:3:4:5:6:7:8:9" in output

    text = (
        "오늘은 화씨 +77°F와 화씨 -10°F, 섭씨 +25°C와 섭씨 -3℃가 함께 "
        "표시되었고, standalone +77°F와 +25℃도 별도로 표시됐다."
    )
    output = transform(text)
    assert "화씨 영상 칠십칠도" in output
    assert "화씨 영하 십도" in output
    assert "섭씨 영상 이십오도" in output
    assert "섭씨 영하 삼도" in output
    assert "화씨 화씨" not in output
    assert "standalone 화씨 영상 칠십칠도와 영상 이십오도도" in output
