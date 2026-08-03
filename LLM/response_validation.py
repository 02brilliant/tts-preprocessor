from __future__ import annotations

from collections import Counter
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
_PROTECTED_LITERAL_PATTERNS = (
    re.compile(r"`[^`\r\n]+`"),
    re.compile(r"\{[^{}\r\n]*\}"),
    re.compile(
        r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+;=%-]+"
    ),
    re.compile(
        r"(?<![A-Za-z0-9_.-])"
        r"(?:/[A-Za-z0-9._-]+|/\d+[가-힣]+){2,}"
    ),
    re.compile(
        r"(?<![A-Za-z0-9_.-])[A-Za-z0-9_]+"
        r"\.[A-Za-z][A-Za-z0-9]{0,9}(?![A-Za-z0-9_.-])"
    ),
    re.compile(
        r"(?<![A-Za-z0-9-])[A-Z][A-Z0-9]*"
        r"(?:-[A-Z0-9]+){2,}(?![A-Za-z0-9-])"
    ),
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

    source_structure = _required_structure(normalized_text)
    output_structure = _required_structure(speech_text)
    if not _preserves_structure_with_allowed_insertions(
        source_structure,
        output_structure,
    ):
        source_index = 0
        for character in output_structure:
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

    source_literals = _protected_literals(normalized_text)
    output_literals = _protected_literals(speech_text)
    if source_literals - output_literals:
        raise LLMStageContractError(
            "LLM response changed or removed a protected URL, path, filename, "
            "JSON, inline-code, or identifier surface.",
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


def _protected_literals(text: str) -> Counter[str]:
    literals: Counter[str] = Counter()
    occupied: list[tuple[int, int]] = []
    for pattern in _PROTECTED_LITERAL_PATTERNS:
        for match in pattern.finditer(text):
            span = match.span()
            if any(
                span[0] < occupied_end and occupied_start < span[1]
                for occupied_start, occupied_end in occupied
            ):
                continue
            literals[match.group(0)] += 1
            occupied.append(span)
    return literals


def _preserves_structure_with_allowed_insertions(
    source_structure: list[str],
    output_structure: list[str],
) -> bool:
    """Match source structure while allowing only inserted comma/ASCII space.

    A newly inserted ASCII space can be identical to the next source space.
    Keep both match and insertion paths so a greedy match cannot consume the
    wrong space and reject an otherwise valid response.
    """

    match_masks: dict[str, int] = {}
    for source_index, character in enumerate(source_structure):
        match_masks[character] = (
            match_masks.get(character, 0) | (1 << source_index)
        )

    reachable = 1
    for character in output_structure:
        next_reachable = (
            reachable & match_masks.get(character, 0)
        ) << 1
        if character in {",", " "}:
            next_reachable |= reachable
        if not next_reachable:
            return False
        reachable = next_reachable
    return bool(reachable & (1 << len(source_structure)))


def _required_structure(text: str) -> list[str]:
    """Return fixed structure, excluding separators consumed by number reading."""

    structure: list[str] = []
    for match in _STRUCTURE_CHARACTER_RE.finditer(text):
        character = match.group(0)
        index = match.start()
        if (
            character in {".", ",", ":"}
            and index > 0
            and index + 1 < len(text)
            and text[index - 1].isascii()
            and text[index - 1].isdigit()
            and text[index + 1].isascii()
            and text[index + 1].isdigit()
        ):
            continue
        structure.append(character)
    return structure
