from __future__ import annotations

import re

from LLM.client import LLMResponseError


_LOCK_TOKEN_RE = re.compile(r"<LOCK_\d+>")
_SPEECH_STRUCTURE_RE = re.compile(
    r"\s+|[,，.。!?！？:：;；()（）\[\]{}\"'“”‘’…—–]+"
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


def validate_prosody_response(normalized_text: str, prosody_text: str) -> str:
    """Require an insert-only prosody result without silently repairing it."""
    if not isinstance(prosody_text, str) or not prosody_text:
        raise LLMResponseError("LLM prosody response is empty.")

    source_index = 0
    for character in prosody_text:
        if (
            source_index < len(normalized_text)
            and character == normalized_text[source_index]
        ):
            source_index += 1
            continue
        if character not in {",", " "}:
            raise LLMResponseError(
                "LLM prosody response changed existing text or added "
                "a character other than comma or ASCII space."
            )

    if source_index != len(normalized_text):
        raise LLMResponseError(
            "LLM prosody response deleted or reordered existing text."
        )
    return prosody_text


def validate_speech_response(prosody_text: str, speech_text: str) -> str:
    """Preserve the prosody structure while allowing pronunciation rewrites."""
    if not isinstance(speech_text, str) or not speech_text:
        raise LLMResponseError("LLM speech response is empty.")

    source_structure = _SPEECH_STRUCTURE_RE.findall(prosody_text)
    output_structure = _SPEECH_STRUCTURE_RE.findall(speech_text)
    if source_structure != output_structure:
        raise LLMResponseError(
            "LLM speech response changed whitespace, line breaks, commas, "
            "or fixed punctuation."
        )

    if _LOCK_TOKEN_RE.findall(prosody_text) != _LOCK_TOKEN_RE.findall(speech_text):
        raise LLMResponseError("LLM speech response changed a locked token.")

    for wrapper in _OUTPUT_WRAPPERS:
        if wrapper not in prosody_text and wrapper in speech_text:
            raise LLMResponseError(
                "LLM speech response added an output wrapper or input tag."
            )
    return speech_text
