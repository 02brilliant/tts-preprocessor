from __future__ import annotations

import re

from LLM.client import LLMResponseError


_LOCK_TOKEN_RE = re.compile(r"<LOCK_\d+>")
_STRUCTURE_CHARACTER_RE = re.compile(
    r"[\s,，.。!?！？:：;；()（）\[\]{}\"'“”‘’…—–]"
)
_OUTPUT_WRAPPERS = (
    "```",
    "~~~",
    "**",
    "__",
    "`",
    "prosody_text:",
    "speech_text:",
    "<NORMALIZED_TEXT>",
    "</NORMALIZED_TEXT>",
    "<PROSODY_TEXT>",
    "</PROSODY_TEXT>",
    "<SPEECH_TEXT>",
    "</SPEECH_TEXT>",
)


class LLMStageContractError(LLMResponseError):
    """A model returned text, but that text violated a stage contract."""

    def __init__(self, message: str, *, stage: str, output_text: str) -> None:
        super().__init__(message)
        self.stage = stage
        self.output_text = output_text


def validate_response(normalized_text: str, speech_text: str) -> str:
    """Validate the integrated pronunciation and prosody response."""
    if not isinstance(speech_text, str) or not speech_text:
        raise LLMResponseError("LLM response is empty.")

    source_structure = _STRUCTURE_CHARACTER_RE.findall(normalized_text)
    source_index = 0
    for character in _STRUCTURE_CHARACTER_RE.findall(speech_text):
        if (
            source_index < len(source_structure)
            and character == source_structure[source_index]
        ):
            source_index += 1
            continue
        if character not in {",", " "}:
            raise LLMStageContractError(
                "LLM response changed existing whitespace, line breaks, "
                "or fixed punctuation, or added a structural character "
                "other than comma or ASCII space.",
                stage="speech",
                output_text=speech_text,
            )
    if source_index != len(source_structure):
        raise LLMStageContractError(
            "LLM response deleted or reordered existing whitespace, "
            "line breaks, or fixed punctuation.",
            stage="speech",
            output_text=speech_text,
        )

    if _LOCK_TOKEN_RE.findall(normalized_text) != _LOCK_TOKEN_RE.findall(speech_text):
        raise LLMStageContractError(
            "LLM response changed a locked token.",
            stage="speech",
            output_text=speech_text,
        )

    for wrapper in _OUTPUT_WRAPPERS:
        if wrapper not in normalized_text and wrapper in speech_text:
            raise LLMStageContractError(
                "LLM response added an output wrapper or input tag.",
                stage="speech",
                output_text=speech_text,
            )
    return speech_text
