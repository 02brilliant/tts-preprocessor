from __future__ import annotations

from pathlib import Path

from LLM.config import PROMPT_PATH


INPUT_PLACEHOLDER = "{{TTS_INPUT_TEXT}}"


class PromptTemplateError(ValueError):
    """Raised when the editable prompt template cannot be used safely."""


def build_prompt(text: str, path: Path = PROMPT_PATH) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    try:
        template = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromptTemplateError("LLM prompt template file is missing.") from exc
    except UnicodeDecodeError as exc:
        raise PromptTemplateError("LLM prompt template must be valid UTF-8.") from exc

    if template.count(INPUT_PLACEHOLDER) != 1:
        raise PromptTemplateError(
            "LLM prompt template must contain exactly one input placeholder."
        )
    return template.replace(INPUT_PLACEHOLDER, text, 1)
