from engine.span_engine.transform import transform


def test_colon_semantic_pair_basic_positive_contexts():
    cases = [
        ("1:2 비율", "일 대 이 비율"),
        ("비율 1:2", "비율 일 대 이"),
        ("16:9 화면비", "십육 대 구 화면비"),
        ("1:100 희석", "일 대 백 희석"),
        ('1.5:2 비율', '일-쩜-오 대 이 비율'),
        ("+1:2 비율", "플러스 일 대 이 비율"),
        ("1:+2 비율", "일 대 플러스 이 비율"),
        ("1:500 축척", "일 대 오백 축척"),
        ("1:100으로 희석", "일 대 백으로 희석"),
        ("2:0으로 이겼다", "이 대 영으로 이겼다"),
        ("3:1 승리", "삼 대 일 승리"),
        ("0:0 무승부", "영 대 영 무승부"),
        ("3:1의 스코어", "삼 대 일의 스코어"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_semantic_pair_expanded_keyword_positive_contexts():
    cases = [
        ("3:0 완승", "삼 대 영 완승"),
        ("5:2 압승", "오 대 이 압승"),
        ("2:1 역전승", "이 대 일 역전승"),
        ("2:1 경기", "이 대 일 경기"),
        ("경기 2:1", "경기 이 대 일"),
        ("3:2 세트", "삼 대 이 세트"),
        ("매치 2:0", "매치 이 대 영"),
        ("게임 1:0", "게임 일 대 영"),
        ("전적 4:3", "전적 사 대 삼"),
        ("배율 1:2", "배율 일 대 이"),
        ("1:2 스케일", "일 대 이 스케일"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_semantic_pair_comma_and_large_number_positive_contexts():
    cases = [
        ("1:1,000,000 축척", "일 대 백만 축척"),
        ("1,000:2,000 비율", "천 대 이천 비율"),
        (
            "99,999,999:1 축척",
            "구천-구백구십구만 구천-구백구십구 대 일 축척",
        ),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_semantic_pair_invalid_numeric_blocks_preserve():
    cases = [
        "01:2 비율",
        "1:02 비율",
        "01,000:2 비율",
        "1:10,00 비율",
        "100,000,000:1 축척",
    ]
    for source in cases:
        assert transform(source) == source


def test_colon_semantic_pair_broad_standalone_and_time_like_preserve():
    positive = [
        ("1:2", "일 대 이"),
        ("1:1,000,000", "일 대 백만"),
    ]
    for source, expected in positive:
        assert transform(source) == expected

    cases = [
        "3:16",
        "10:20",
    ]
    for source in cases:
        assert transform(source) == source


def test_colon_semantic_pair_adjacent_korean_tail_spacing():
    cases = [
        ("3:4테스트", "삼 대 사 테스트"),
        ("+1:2테스트", "플러스 일 대 이 테스트"),
        ('1.5:2.0범위', '일-쩜-오 대 이-쩜-영 범위'),
        ("1,000:2,000테스트", "천 대 이천 테스트"),
        ("3：4테스트", "삼 대 사 테스트"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_semantic_pair_scripture_like_inputs_remain_ambiguous():
    cases = [
        "요한복음 3:16",
        "창세기 1:05",
        "문서 3:16",
        "참조 10:20",
    ]
    for source in cases:
        assert transform(source) == source


def test_colon_semantic_pair_duration_media_inputs_remain_out_of_scope():
    cases = [
        "영상 1:23",
        "재생시간 03:15",
        "타임라인 10:20",
    ]
    for source in cases:
        assert transform(source) == source


def test_colon_semantic_pair_tail_gates():
    positive = [
        ("2:0으로 이겼다", "이 대 영으로 이겼다"),
        ("3:1로 승리", "삼 대 일로 승리"),
        ("1:100으로 희석", "일 대 백으로 희석"),
        ("1:2의 비율", "일 대 이의 비율"),
        ("16:9의 화면비", "십육 대 구의 화면비"),
    ]
    for source, expected in positive:
        assert transform(source) == expected

    broad = [
        ("2:0으로 끝났다", "이 대 영으로 끝났다"),
        ("3:1로 마무리", "삼 대 일로 마무리"),
        ("1:2로 섞었다", "일 대 이로 섞었다"),
    ]
    for source, expected in broad:
        assert transform(source) == expected


def test_colon_semantic_pair_time_owner_precedence_and_time_like_rejection():
    cases = [
        ("13:05에 시작", "십삼시 오분에 시작"),
        ("14:00부터", "십사시부터"),
        ("오전 9:30", "오전 아홉시 삼십분"),
        ("회의 14:00", "회의 십사시"),
        ("2:00에 시작", "두시에 시작"),
        ("1:05 비율", "1:05 비율"),
        ("2:00 승리", "2:00 승리"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_semantic_pair_protected_and_code_like_contexts():
    text = "`1:2 비율` 옆 25℃와 3kg은 처리해야 합니다."
    out = transform(text)
    assert out != text
    assert "`1:2 비율`" in out
    assert "이십오도" in out
    assert "삼-킬로그램" in out

    for source in (
        "line 10:20",
        "case 3:16",
        "/path/1:2/log",
        '{"ratio":"1:2"}',
    ):
        assert transform(source) == source


def test_colon_semantic_pair_fullwidth_colon_equivalence():
    positive = [
        ("1：2 비율", "일 대 이 비율"),
        ("2：0으로 이겼다", "이 대 영으로 이겼다"),
    ]
    for source, expected in positive:
        assert transform(source) == expected

    cases = [
        ("13：05에 시작", "십삼시 오분에 시작"),
        ("13：05", "십삼시 오분"),
        ("요한복음 3：16", "요한복음 3：16"),
        ("영상 1：23", "영상 1：23"),
        ("`1：2 비율`", "`1：2 비율`"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_colon_semantic_pair_neighbors_still_transform():
    text = "1:2 비율과 25℃, $25.99, 3kg는 모두 확인합니다."
    out = transform(text)
    assert out != text
    assert "일 대 이 비율" in out
    assert "이십오도" in out
    assert "이십오-쩜-구구-달러" in out
    assert "삼-킬로그램" in out

    text = "1：2 비율과 25℃, $25.99, 3kg는 모두 확인합니다."
    out = transform(text)
    assert out != text
    assert "일 대 이 비율" in out
    assert "이십오도" in out
    assert "이십오-쩜-구구-달러" in out
    assert "삼-킬로그램" in out
