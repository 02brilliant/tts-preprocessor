from __future__ import annotations

from pathlib import Path

from LLM.config import PROSODY_PROMPT_PATH, SPEECH_PROMPT_PATH


PROSODY_INPUT_PLACEHOLDER = "{{NORMALIZED_TEXT}}"
SPEECH_INPUT_PLACEHOLDER = "{{PROSODY_TEXT}}"
PROSODY_PROMPT_FILE_LABEL = "LLM/docs/LLM_prompt_prosody.txt"
SPEECH_PROMPT_FILE_LABEL = "LLM/docs/LLM_prompt_speech.txt"


class PromptTemplateError(ValueError):
    """Raised when the editable prompt template cannot be used safely."""


def _build_prompt(
    text: str,
    *,
    path: Path,
    placeholder: str,
    file_label: str,
) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    try:
        template = path.read_text(encoding="utf-8")
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

    placeholder_count = template.count(placeholder)
    if placeholder_count == 0:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})에 "
            f"{placeholder} 자리표시자가 없습니다. "
            "원고를 넣을 위치에 이 자리표시자를 정확히 한 번 추가한 뒤 다시 실행하세요."
        )
    if placeholder_count > 1:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})에 "
            f"{placeholder} 자리표시자가 {placeholder_count}개 있습니다. "
            "하나만 남긴 뒤 다시 실행하세요."
        )
    return template.replace(placeholder, text, 1)


def build_prosody_prompt(
    normalized_text: str,
    path: Path = PROSODY_PROMPT_PATH,
) -> str:
    return _build_prompt(
        normalized_text,
        path=path,
        placeholder=PROSODY_INPUT_PLACEHOLDER,
        file_label=PROSODY_PROMPT_FILE_LABEL,
    )


def build_speech_prompt(
    prosody_text: str,
    path: Path = SPEECH_PROMPT_PATH,
) -> str:
    return _build_prompt(
        prosody_text,
        path=path,
        placeholder=SPEECH_INPUT_PLACEHOLDER,
        file_label=SPEECH_PROMPT_FILE_LABEL,
    )
