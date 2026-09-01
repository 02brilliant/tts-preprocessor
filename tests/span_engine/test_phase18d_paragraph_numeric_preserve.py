from __future__ import annotations

from engine.span_engine import transform


def _long_numeric_paragraph() -> str:
    return (
        "보고서에는 12,345,678,901원과 3.5톤과 250m/L이 포함되어 "
        "재무팀과 물류팀이 함께 검토할 예정이며 이 문장은 의도적으로 길게 작성합니다. "
        "첫 번째 설명은 현재 정책 검증을 위해 충분히 길게 작성되어 여러 조건과 배경을 차분하게 이어서 말합니다. "
        "두 번째 설명도 같은 주제를 이어 가며 일정과 예산과 결과를 자세히 정리하여 전체 문단 길이를 안정적으로 늘립니다. "
        "세 번째 설명 역시 앞선 내용과 같은 흐름을 유지하며 독자가 숫자와 일반 서술을 함께 듣는 상황을 가정합니다. "
        "한편 마지막 설명은 다른 주제로 전환되어 후속 계획과 검토 항목을 분명하게 알립니다."
    )


def test_phase18d_long_numeric_paragraph_splits_without_changing_readings() -> None:
    text = _long_numeric_paragraph()
    output = transform(text)
    collapsed = output.replace("\n", "")

    assert "\n" in output
    assert "3.5톤" not in collapsed
    assert "250m/L" not in collapsed
    assert "삼-쩜-오톤" in collapsed
    assert "리터당" in collapsed
    assert "한편" in collapsed
