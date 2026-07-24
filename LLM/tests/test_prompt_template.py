from __future__ import annotations

from pathlib import Path

import pytest

from LLM.prompt_template import PromptTemplateError, build_prompt


def test_prompt_replaces_exactly_one_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("앞\n{{TTS_INPUT_TEXT}}\n뒤", encoding="utf-8")

    assert build_prompt("원고", path) == "앞\n원고\n뒤"


def test_prompt_explains_how_to_fix_missing_placeholder(
    tmp_path: Path,
) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("자리표시자 없음", encoding="utf-8")

    with pytest.raises(PromptTemplateError) as exc_info:
        build_prompt("원고", path)

    assert str(exc_info.value) == (
        "AI LLM 프롬프트 파일(LLM/docs/LLM_prompt.txt)에 "
        "{{TTS_INPUT_TEXT}} 자리표시자가 없습니다. "
        "원고를 넣을 위치에 이 자리표시자를 정확히 한 번 추가한 뒤 다시 실행하세요."
    )


def test_prompt_explains_how_to_fix_duplicate_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("{{TTS_INPUT_TEXT}}\n{{TTS_INPUT_TEXT}}", encoding="utf-8")

    with pytest.raises(PromptTemplateError) as exc_info:
        build_prompt("원고", path)

    assert str(exc_info.value) == (
        "AI LLM 프롬프트 파일(LLM/docs/LLM_prompt.txt)에 "
        "{{TTS_INPUT_TEXT}} 자리표시자가 2개 있습니다. "
        "하나만 남긴 뒤 다시 실행하세요."
    )


def test_prompt_explains_how_to_fix_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_bytes(b"\xff")

    with pytest.raises(PromptTemplateError) as exc_info:
        build_prompt("원고", path)

    assert str(exc_info.value) == (
        "AI LLM 프롬프트 파일(LLM/docs/LLM_prompt.txt)은 UTF-8 인코딩이어야 합니다. "
        "파일을 UTF-8로 저장한 뒤 다시 실행하세요."
    )


def test_prompt_explains_how_to_fix_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.txt"

    with pytest.raises(PromptTemplateError) as exc_info:
        build_prompt("원고", path)

    assert str(exc_info.value) == (
        "AI LLM 프롬프트 파일(LLM/docs/LLM_prompt.txt)을 찾을 수 없습니다. "
        "파일을 복원한 뒤 다시 실행하세요."
    )


def test_prompt_reloads_file_for_each_request(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("첫째 {{TTS_INPUT_TEXT}}", encoding="utf-8")
    assert build_prompt("원고", path) == "첫째 원고"

    path.write_text("둘째 {{TTS_INPUT_TEXT}}", encoding="utf-8")
    assert build_prompt("원고", path) == "둘째 원고"
