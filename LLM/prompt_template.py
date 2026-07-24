from __future__ import annotations

from pathlib import Path

from LLM.config import PROMPT_PATH


INPUT_PLACEHOLDER = "{{TTS_INPUT_TEXT}}"
PROMPT_FILE_LABEL = "LLM/docs/LLM_prompt.txt"


class PromptTemplateError(ValueError):
    """Raised when the editable prompt template cannot be used safely."""


def build_prompt(text: str, path: Path = PROMPT_PATH) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    try:
        template = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({PROMPT_FILE_LABEL})을 찾을 수 없습니다. "
            "파일을 복원한 뒤 다시 실행하세요."
        ) from exc
    except UnicodeDecodeError as exc:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({PROMPT_FILE_LABEL})은 UTF-8 인코딩이어야 합니다. "
            "파일을 UTF-8로 저장한 뒤 다시 실행하세요."
        ) from exc

    placeholder_count = template.count(INPUT_PLACEHOLDER)
    if placeholder_count == 0:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({PROMPT_FILE_LABEL})에 "
            f"{INPUT_PLACEHOLDER} 자리표시자가 없습니다. "
            "원고를 넣을 위치에 이 자리표시자를 정확히 한 번 추가한 뒤 다시 실행하세요."
        )
    if placeholder_count > 1:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({PROMPT_FILE_LABEL})에 "
            f"{INPUT_PLACEHOLDER} 자리표시자가 {placeholder_count}개 있습니다. "
            "하나만 남긴 뒤 다시 실행하세요."
        )
    return template.replace(INPUT_PLACEHOLDER, text, 1)
