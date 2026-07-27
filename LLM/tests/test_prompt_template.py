from __future__ import annotations

from pathlib import Path

import pytest

from LLM.prompt_template import (
    PromptTemplateError,
    build_prosody_prompt,
    build_speech_prompt,
)


@pytest.mark.parametrize(
    ("builder", "placeholder"),
    (
        (build_prosody_prompt, "{{NORMALIZED_TEXT}}"),
        (build_speech_prompt, "{{PROSODY_TEXT}}"),
    ),
)
def test_stage_prompt_replaces_exactly_one_placeholder(
    tmp_path: Path,
    builder,
    placeholder: str,
) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text(f"앞\n{placeholder}\n뒤", encoding="utf-8")

    assert builder("원고", path) == "앞\n원고\n뒤"


@pytest.mark.parametrize(
    ("builder", "placeholder", "file_label"),
    (
        (
            build_prosody_prompt,
            "{{NORMALIZED_TEXT}}",
            "LLM/docs/LLM_prompt_prosody.txt",
        ),
        (
            build_speech_prompt,
            "{{PROSODY_TEXT}}",
            "LLM/docs/LLM_prompt_speech.txt",
        ),
    ),
)
def test_stage_prompt_reports_missing_placeholder(
    tmp_path: Path,
    builder,
    placeholder: str,
    file_label: str,
) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("자리표시자 없음", encoding="utf-8")

    with pytest.raises(PromptTemplateError) as exc_info:
        builder("원고", path)

    assert str(exc_info.value) == (
        f"AI LLM 프롬프트 파일({file_label})에 "
        f"{placeholder} 자리표시자가 없습니다. "
        "원고를 넣을 위치에 이 자리표시자를 정확히 한 번 추가한 뒤 다시 실행하세요."
    )


@pytest.mark.parametrize(
    ("builder", "placeholder", "file_label"),
    (
        (
            build_prosody_prompt,
            "{{NORMALIZED_TEXT}}",
            "LLM/docs/LLM_prompt_prosody.txt",
        ),
        (
            build_speech_prompt,
            "{{PROSODY_TEXT}}",
            "LLM/docs/LLM_prompt_speech.txt",
        ),
    ),
)
def test_stage_prompt_reports_duplicate_placeholder(
    tmp_path: Path,
    builder,
    placeholder: str,
    file_label: str,
) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text(f"{placeholder}\n{placeholder}", encoding="utf-8")

    with pytest.raises(PromptTemplateError) as exc_info:
        builder("원고", path)

    assert str(exc_info.value) == (
        f"AI LLM 프롬프트 파일({file_label})에 "
        f"{placeholder} 자리표시자가 2개 있습니다. "
        "하나만 남긴 뒤 다시 실행하세요."
    )


@pytest.mark.parametrize(
    ("builder", "file_label"),
    (
        (build_prosody_prompt, "LLM/docs/LLM_prompt_prosody.txt"),
        (build_speech_prompt, "LLM/docs/LLM_prompt_speech.txt"),
    ),
)
def test_stage_prompt_reports_invalid_utf8(
    tmp_path: Path,
    builder,
    file_label: str,
) -> None:
    path = tmp_path / "prompt.txt"
    path.write_bytes(b"\xff")

    with pytest.raises(PromptTemplateError) as exc_info:
        builder("원고", path)

    assert str(exc_info.value) == (
        f"AI LLM 프롬프트 파일({file_label})은 UTF-8 인코딩이어야 합니다. "
        "파일을 UTF-8로 저장한 뒤 다시 실행하세요."
    )


@pytest.mark.parametrize(
    ("builder", "file_label"),
    (
        (build_prosody_prompt, "LLM/docs/LLM_prompt_prosody.txt"),
        (build_speech_prompt, "LLM/docs/LLM_prompt_speech.txt"),
    ),
)
def test_stage_prompt_reports_missing_file(
    tmp_path: Path,
    builder,
    file_label: str,
) -> None:
    path = tmp_path / "missing.txt"

    with pytest.raises(PromptTemplateError) as exc_info:
        builder("원고", path)

    assert str(exc_info.value) == (
        f"AI LLM 프롬프트 파일({file_label})을 찾을 수 없습니다. "
        "파일을 복원한 뒤 다시 실행하세요."
    )


@pytest.mark.parametrize(
    ("builder", "placeholder"),
    (
        (build_prosody_prompt, "{{NORMALIZED_TEXT}}"),
        (build_speech_prompt, "{{PROSODY_TEXT}}"),
    ),
)
def test_stage_prompt_reloads_file_for_each_request(
    tmp_path: Path,
    builder,
    placeholder: str,
) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text(f"첫째 {placeholder}", encoding="utf-8")
    assert builder("원고", path) == "첫째 원고"

    path.write_text(f"둘째 {placeholder}", encoding="utf-8")
    assert builder("원고", path) == "둘째 원고"
