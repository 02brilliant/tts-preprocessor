from engine.main import transform


def test_policy_megacase_detects_cross_layer_conflicts():
    text = (
        "회의(비공개) [긴급] 일정은 오전 9시 안내 후 12:30에 시작한다. "
        "그리고 2026-04-17 예산은 ₩1200이며 이동 거리는 3.14km이고 "
        "5·18 민주화운동 자료는 21명에게 배포한다."
    )
    expected = (
        "회의 긴급 일정은 오전 아홉시 안내 후 열두시 삼십분에 시작한다. "
        "그리고, 이천이십육년 사월 십칠일 예산은 천이백 원이며 이동 거리는 "
        "삼쩜일사 킬로미터이고 오일팔 민주화운동 자료는 스물한 명에게 배포한다."
    )
    assert transform(text) == expected
