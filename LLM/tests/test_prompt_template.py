from __future__ import annotations

from pathlib import Path

import pytest

from LLM.config import LLM_PROMPT_PATH
from LLM.prompt_template import PromptTemplateError, build_prompt


def test_prompt_replaces_exactly_one_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("앞\n{{NORMALIZED_TEXT}}\n뒤", encoding="utf-8")

    assert build_prompt("원고", path) == "앞\n원고\n뒤"


def test_prompt_reports_missing_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("자리표시자 없음", encoding="utf-8")

    with pytest.raises(PromptTemplateError) as exc_info:
        build_prompt("원고", path)

    assert str(exc_info.value) == (
        "AI LLM 프롬프트 파일(LLM/docs/LLM_prompt.txt)에 "
        "{{NORMALIZED_TEXT}} 자리표시자가 없습니다. "
        "원고를 넣을 위치에 이 자리표시자를 정확히 한 번 추가한 뒤 다시 실행하세요."
    )


def test_prompt_reports_duplicate_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text(
        "{{NORMALIZED_TEXT}}\n{{NORMALIZED_TEXT}}",
        encoding="utf-8",
    )

    with pytest.raises(PromptTemplateError) as exc_info:
        build_prompt("원고", path)

    assert str(exc_info.value) == (
        "AI LLM 프롬프트 파일(LLM/docs/LLM_prompt.txt)에 "
        "{{NORMALIZED_TEXT}} 자리표시자가 2개 있습니다. "
        "하나만 남긴 뒤 다시 실행하세요."
    )


def test_prompt_reports_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_bytes(b"\xff")

    with pytest.raises(PromptTemplateError) as exc_info:
        build_prompt("원고", path)

    assert str(exc_info.value) == (
        "AI LLM 프롬프트 파일(LLM/docs/LLM_prompt.txt)은 UTF-8 인코딩이어야 합니다. "
        "파일을 UTF-8로 저장한 뒤 다시 실행하세요."
    )


def test_prompt_reports_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.txt"

    with pytest.raises(PromptTemplateError) as exc_info:
        build_prompt("원고", path)

    assert str(exc_info.value) == (
        "AI LLM 프롬프트 파일(LLM/docs/LLM_prompt.txt)을 찾을 수 없습니다. "
        "파일을 복원한 뒤 다시 실행하세요."
    )


def test_prompt_reloads_file_for_each_request(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("첫째 {{NORMALIZED_TEXT}}", encoding="utf-8")
    assert build_prompt("원고", path) == "첫째 원고"

    path.write_text("둘째 {{NORMALIZED_TEXT}}", encoding="utf-8")
    assert build_prompt("원고", path) == "둘째 원고"


def test_active_prompt_has_contextual_number_unit_handoff_contract() -> None:
    prompt = LLM_PROMPT_PATH.read_text(encoding="utf-8")

    assert prompt.count("{{NORMALIZED_TEXT}}") == 1
    assert (
        "입력은 규칙 기반 엔진의 최종 읽기 문자열 하나뿐이다."
        in prompt
    )
    assert (
        "보호 대상이 아닌 숫자나 영문 표면을 최종 출력에 남기지 않는다."
        in prompt
    )
    assert "3번 확인했다 -> 세 번 확인했다" in prompt
    assert "5분이 남았다. -> 오분이 남았다." in prompt
    assert "3층을 올라갔다 -> 세 층을 올라갔다" in prompt
    assert "총 2.34번 -> 총 이쩜삼사 번" in prompt


def test_active_prompt_locks_rule_canonical_readings_and_spacing() -> None:
    prompt = LLM_PROMPT_PATH.read_text(encoding="utf-8")

    for fixed_reading in ("삼번 버스", "오분 뒤", "제 삼장"):
        assert fixed_reading in prompt

    for superseded_reading in (
        "회의는 오 분 뒤 시작하며",
        "참석자는 삼 번 버스를",
        "제3장 -> 제삼장",
        "보호 구간 밖에 아라비아 숫자가 남는 것은 허용된다",
    ):
        assert superseded_reading not in prompt


def test_active_prompt_injects_only_plain_normalized_text() -> None:
    normalized_text = "3번 확인했고 5분이 남았다."

    rendered = build_prompt(normalized_text)

    assert (
        "<NORMALIZED_TEXT>\n"
        f"{normalized_text}\n"
        "</NORMALIZED_TEXT>"
    ) in rendered
    assert "<CONTEXTUAL_DECISION_LOGS>" not in rendered
    assert "<DECISION_CANDIDATES>" not in rendered
