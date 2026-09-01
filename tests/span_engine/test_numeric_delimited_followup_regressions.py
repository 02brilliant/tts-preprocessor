from __future__ import annotations

from engine.span_engine.transform import transform


def test_full_width_and_mixed_colon_multi_colon_regressions() -> None:
    cases = [
        ("1：2：3", "일 대 이 대 삼"),
        ("1：2：3：4", "일 대 이 대 삼 대 사"),
        ("+1：2：3：4", "플러스 일 대 이 대 삼 대 사"),
        ("1:2：3:4", "일 대 이 대 삼 대 사"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_plus_start_and_mixed_sign_multi_colon_regressions() -> None:
    cases = [
        ("+1:2:3", "플러스 일 대 이 대 삼"),
        ("+1:2:-3:4", "플러스 일 대 이 대 마이너스 삼 대 사"),
        ("1:+2:-3:4", "일 대 플러스 이 대 마이너스 삼 대 사"),
        ("-1:+2:-3:4", "마이너스 일 대 플러스 이 대 마이너스 삼 대 사"),
    ]
    for source, expected in cases:
        assert transform(source) == expected

    for source in (
        "+1:02:03",
        "+01:2:3",
        "1:+2.:3",
        "1:+2:+3:+4:+5:+6:+7:+8:+9",
    ):
        assert transform(source) == source


def test_multi_colon_guard_boundary_regressions() -> None:
    assert (
        transform("multi-colon 값 1:2:3:4:5:6:7:8")
        == "multi-colon 값 일 대 이 대 삼 대 사 대 오 대 육 대 칠 대 팔"
    )
    assert transform("ordinary-text 1:2:3") == "ordinary-text 일 대 이 대 삼"

    for source in (
        "line 10:20:30",
        "case 1:2:3:4",
        "version 1:2:3",
        "/path/1:2:3:4/log",
        "`1:2:3:4`",
    ):
        assert transform(source) == source


def test_plus_comma_decimal_krw_currency_regressions() -> None:
    cases = [
        ("+1,000원", "플러스 천-원"),
        ('+1,000.50원', '플러스 천-쩜-오영-원'),
        ('보정값은 +1,000.50원', '보정값은 플러스 천-쩜-오영-원'),
        ("+25℃", "영상 이십오도"),
        ("+77°F", "화씨 영상 칠십칠도"),
        ("+25kg", "플러스 이십오-킬로그램"),
        ("+25%", "플러스 이십오-퍼센트"),
    ]
    for source, expected in cases:
        assert transform(source) == expected

    for source in (
        "+1,00.5원",
        "+01원",
        "/path/+1,000.50원/log",
        "`+1,000.50원`",
    ):
        assert transform(source) == source


def test_math_like_expression_whole_preserve_regressions() -> None:
    for source in (
        "x+y=3",
        "a+=1",
        "A+B",
        "foo+bar",
        "C++17",
        "x-y=3",
        "a-=1",
        "x*2=4",
        "x/2=3",
        "x+y+z=10",
        "a==1",
        "a>=1",
        "a<=1",
    ):
        assert transform(source) == source

    assert transform("값은 +1입니다") == "값은 플러스 일입니다"
    assert transform("오차는 +1.5kg입니다") == '오차는 플러스 일-쩜-오-킬로그램입니다'
    assert transform("비율은 +1:2 비율입니다") == "비율은 플러스 일 대 이 비율입니다"


def test_observed_long_sentence_regressions() -> None:
    cases = [
        (
            "혼합 구분자 테스트로 1：2：3, 1:2：3:4, +1:2:+3:4를 입력했고, 모두 colon-like delimiter 정책을 따라야 한다.",
            [
                "일 대 이 대 삼",
                "일 대 이 대 삼 대 사",
                "플러스 일 대 이 대 플러스 삼 대 사",
            ],
        ),
        (
            "오늘 실험에서는 +25℃ 환경에서 +1.5kg 시료를 사용했고, 보정 비율은 +1.2:2.3 비율, 배열 값은 +1:2:-3:4, 허용 범위는 -2.3~+4.5kg으로 기록했으며, 경로 /path/+1:2/log는 변환하지 않았다.",
            [
                "영상 이십오도",
                "플러스 일-쩜-오-킬로그램",
                "플러스 일-쩜-이 대 이-쩜-삼 비율",
                "플러스 일 대 이 대 마이너스 삼 대 사",
                "마이너스 이-쩜-삼에서 플러스 사-쩜-오-킬로그램",
                "/path/+1:2/log",
            ],
        ),
        (
            "보고서에는 화씨 +77°F, 섭씨 -3℃, 전화번호 +82-10-1234-5678, 화면비 16:9 화면비, multi-colon 값 1:2:3:4:5:6:7:8, 그리고 초과 블럭 1:2:3:4:5:6:7:8:9가 함께 포함되어 있다.",
            [
                "화씨 영상 칠십칠도",
                "영하 삼도",
                "플러스 팔이 일공 일이삼사 오육칠팔",
                "십육 대 구 화면비",
                "일 대 이 대 삼 대 사 대 오 대 육 대 칠 대 팔",
                "1:2:3:4:5:6:7:8:9",
            ],
        ),
        (
            "알림 문구는 “전화번호 +1-800-123-4567로 연락하고, 온도는 +25℃를 유지하며, 보정값은 +1,000.50원, 비율은 +1,000.50:2 스케일로 입력하세요”이다.",
            [
                "플러스 일 팔공공 일이삼 사오육칠",
                "영상 이십오도",
                "플러스 천-쩜-오영-원",
                "플러스 천-쩜-오영 대 이 스케일",
            ],
        ),
        (
            "혼합 delimiter 예시는 1：2 비율, 1：2：3, +1：2：3：4, -2.3∼+4.5kg, +1.5〜+2.0cm로 구성한다.",
            [
                "일 대 이 비율",
                "일 대 이 대 삼",
                "플러스 일 대 이 대 삼 대 사",
                "마이너스 이-쩜-삼에서 플러스 사-쩜-오-킬로그램",
                "플러스 일-쩜-오에서 플러스 이-쩜-영-센티미터",
            ],
        ),
        (
            "문장 안에는 +25, +25kg, +25%, +25℃, +77°F, +1:2 비율, +1:2, +1:2:3, +1:02:03이 모두 있으며, 각각의 owner precedence가 달라야 한다.",
            [
                "플러스 이십오",
                "플러스 이십오-킬로그램",
                "플러스 이십오-퍼센트",
                "영상 이십오도",
                "화씨 영상 칠십칠도",
                "플러스 일 대 이 비율",
                "플러스 일 대 이",
                "플러스 일 대 이 대 삼",
                "+1:02:03",
            ],
        ),
        (
            "C++17, A+B, x+y=3, foo+bar, a+=1은 plus numeric sign으로 처리하지 않고 그대로 두어야 한다.",
            ["C++17", "A+B", "x+y=3", "foo+bar", "a+=1"],
        ),
    ]
    for source, expected_fragments in cases:
        output = transform(source)
        for fragment in expected_fragments:
            assert fragment in output
