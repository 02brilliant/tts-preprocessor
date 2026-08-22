from __future__ import annotations

from pathlib import Path

from LLM.config import LLM_PROMPT_LV2_PATH, LLM_PROMPT_PATH


INPUT_PLACEHOLDER = "{{NORMALIZED_TEXT}}"
PROMPT_FILE_LABEL = "LLM/docs/LLM_prompt.txt"
PROMPT_LV2_FILE_LABEL = "LLM/docs/LLM_prompt_lv2.txt"
PROMPT_PATHS = {
    1: (LLM_PROMPT_PATH, PROMPT_FILE_LABEL),
    2: (LLM_PROMPT_LV2_PATH, PROMPT_LV2_FILE_LABEL),
}


class PromptTemplateError(ValueError):
    """Raised when the editable prompt template cannot be used safely."""


def build_prompt(
    normalized_text: str,
    path: Path | None = None,
    *,
    prompt_level: int = 1,
) -> str:
    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be a string")

    if isinstance(prompt_level, bool) or prompt_level not in PROMPT_PATHS:
        raise PromptTemplateError("LLM prompt_level must be 1 or 2.")

    configured_path, configured_label = PROMPT_PATHS[prompt_level]
    selected_path = path if path is not None else configured_path
    file_label = PROMPT_FILE_LABEL if path is not None else configured_label

    try:
        template = selected_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})을 찾을 수 없습니다. "
            "파일을 복원한 뒤 다시 실행하세요."
        ) from exc
    except UnicodeDecodeError as exc:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})은 UTF-8 인코딩이어야 합니다. "
            "파일을 UTF-8로 저장한 뒤 다시 실행하세요."
        ) from exc

    placeholder_count = template.count(INPUT_PLACEHOLDER)
    if placeholder_count == 0:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})에 "
            f"{INPUT_PLACEHOLDER} 자리표시자가 없습니다. "
            "원고를 넣을 위치에 이 자리표시자를 정확히 한 번 추가한 뒤 다시 실행하세요."
        )
    if placeholder_count > 1:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})에 "
            f"{INPUT_PLACEHOLDER} 자리표시자가 {placeholder_count}개 있습니다. "
            "하나만 남긴 뒤 다시 실행하세요."
        )
    return template.replace(INPUT_PLACEHOLDER, normalized_text, 1)
