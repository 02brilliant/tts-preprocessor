from __future__ import annotations

import re

from LLM.client import LLMResponseError
from LLM.pronunciation_lexicon import build_allowed_mutations
from LLM.provenance import minimal_snapshot
from LLM.validation_models import (
    AllowedMutation,
    NormalizationSnapshot,
    ValidationIssue,
    ValidationResult,
)
from engine.span_engine.counter import native_number_under_100
from engine.span_engine.date_time import is_valid_time, time_number_reading
from engine.span_engine.language_gate import is_non_korean_prose_line
from engine.span_engine.numeric_reading import read_number_text


_STRUCTURE_CHARACTER_RE = re.compile(
    r"[\s,，.。!?！？:：;；()（）\[\]{}\"'“”‘’…—–]"
)
_CONFIRMED_KBS_NEWS_RE = re.compile(
    r"(?<![A-Za-z0-9_])KBS news(?![A-Za-z0-9_])"
)
_LEADING_TIME_FRAME_RE = re.compile(
    r"^[ \t]*(?P<phrase>"
    r"(?:지난해|올해|내년)\s+(?:"
    r"[가-힣]+월부터\s+[가-힣]+월까지(?:는)?"
    r"|[가-힣]+월\s+[가-힣]+일(?:부터는|까지는|에서는|에는|에도|부터|까지|에서|에)?"
    r"|(?:상반기|하반기|[가-힣]+분기|[가-힣]+월)"
    r"(?:부터는|까지는|에서는|에는|에도|부터|까지|에서|에)?"
    r")"
    r"|(?:오늘|내일|어제)\s+(?:아침|오전|오후|저녁)"
    r"|(?:오늘|내일)\s+서울에서"
    r"|(?:지난달|지난해|올해)"
    r"|(?:이번\s+주|다음\s+주)"
    r"|지난\s+(?:\d+|[가-힣]+)일"
    r")(?=\s|,|[.!?]|$)"
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
_RESIDUAL_RUN_RE = re.compile(r"[A-Za-z0-9%‰℃℉°₩$€£¥+×÷=<>±~/:.,_-]+")
_RESIDUAL_OUTPUT_PATTERN = r"[가-힣A-Za-z0-9%‰℃℉°₩$€£¥+×÷=<>±~/:.,_·\- \t]+?"
_NUMERIC_CORE_RE = re.compile(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?")
_COLON_TIME_RE = re.compile(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})")
_COMPATIBILITY_JAMO_RE = re.compile(r"[ㄱ-ㅎㅏ-ㅣ]")
_SPECIAL_SPACE_RE = re.compile(r"[\u00a0\u1680\u2000-\u200b\u202f\u205f\u3000\ufeff]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_DISALLOWED_DASHES = frozenset("‐‑‒–—―−﹘﹣－")
_SEMANTIC_GUARD_RE = re.compile(r"않|못|아니|없")
_SPEECH_TARGET_RESIDUAL_RE = re.compile(
    r"[A-Za-z0-9]|[%‰℃℉°₩$€£¥+×÷=<>±]"
)


class LLMStageContractError(LLMResponseError):
    """A model returned text, but that text violated a stage contract."""

    def __init__(
        self,
        message: str,
        *,
        stage: str,
        output_text: str,
        code: str = "LLM_STAGE_CONTRACT",
        severity: str = "High",
        output_start: int | None = None,
        output_end: int | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.output_text = output_text
        self.code = code
        self.severity = severity
        self.output_start = output_start
        self.output_end = output_end


def validate_response(
    normalized_text: str,
    speech_text: str,
    *,
    prompt_level: int = 2,
    snapshot: NormalizationSnapshot | None = None,
) -> str:
    """Validate an LLM response and raise for a Critical/High violation."""
    if not isinstance(speech_text, str) or not speech_text:
        raise LLMResponseError("LLM response is empty.")
    if isinstance(prompt_level, bool) or prompt_level not in {1, 2}:
        raise ValueError("prompt_level must be 1 or 2")

    result = validate_speech_text(
        normalized_text,
        speech_text,
        stage=prompt_level + 2,
        snapshot=snapshot,
    )
    if not result.ok:
        issue = result.issues[0]
        raise LLMStageContractError(
            issue.message,
            stage="speech",
            output_text=speech_text,
            code=issue.code,
            severity=issue.severity,
            output_start=issue.output_start,
            output_end=issue.output_end,
        )
    return speech_text


def validate_speech_text(
    normalized_text: str,
    speech_text: str,
    *,
    stage: int,
    snapshot: NormalizationSnapshot | None = None,
    candidates: tuple[AllowedMutation, ...] | None = None,
) -> ValidationResult:
    if not isinstance(normalized_text, str) or not isinstance(speech_text, str):
        raise TypeError("normalized_text and speech_text must be str")
    if stage not in {3, 4}:
        raise ValueError("stage must be 3 or 4")
    if not speech_text:
        return _failure("EMPTY_RESPONSE", "Critical", "LLM response is empty.")

    active_snapshot = snapshot or minimal_snapshot(normalized_text)
    if active_snapshot.normalized_text != normalized_text:
        raise ValueError("snapshot does not match normalized_text")
    active_candidates = candidates
    if active_candidates is None:
        active_candidates = build_allowed_mutations(
            normalized_text,
            stage=stage,
            snapshot=active_snapshot,
        )

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
                return _failure(
                    "SENTENCE_STRUCTURE_MUTATION",
                    "Critical",
                    "LLM response changed existing whitespace, line breaks, "
                    "or fixed punctuation, or added a structural character "
                    "other than comma or ASCII space.",
                )
        return _failure(
            "SENTENCE_STRUCTURE_MUTATION",
            "Critical",
            "LLM response deleted or reordered existing whitespace, "
            "line breaks, or fixed punctuation.",
        )

    if _CONFIRMED_KBS_NEWS_RE.findall(
        normalized_text
    ) != _CONFIRMED_KBS_NEWS_RE.findall(speech_text):
        return _failure(
            "LOCKED_READING_MUTATION",
            "Critical",
            "LLM response changed a rule-engine confirmed KBS news reading.",
        )

    if _adds_comma_to_stage1_leading_time_frame(normalized_text, speech_text):
        return _failure(
            "PROSODY_POLICY_VIOLATION",
            "High",
            "LLM response added a comma at a rule-engine confirmed leading "
            "time-frame boundary.",
        )

    policy_pattern = _compile_allowed_output_pattern(
        normalized_text,
        active_snapshot,
        active_candidates,
    )
    if policy_pattern.fullmatch(speech_text) is None:
        if speech_text == normalized_text:
            residual_span = _find_unprotected_residual_surface(
                speech_text,
                active_snapshot,
            )
            if residual_span is not None:
                return _failure(
                    "RESIDUAL_SPEECH_SURFACE",
                    "Medium",
                    "LLM response left a speech-target digit, English letter, or unit symbol.",
                    output_start=residual_span[0],
                    output_end=residual_span[1],
                )
        if not _preserves_residual_numeric_meaning(
            normalized_text,
            speech_text,
            active_snapshot,
        ):
            return _failure(
                "NUMERIC_MEANING_MUTATION",
                "Critical",
                "LLM response changed the value of a residual numeric surface.",
            )
        protected = [span for span in active_snapshot.spans if span.protected]
        if any(span.text not in speech_text for span in protected):
            return _failure(
                "PROTECTED_SPAN_MUTATION",
                "Critical",
                "LLM response changed or removed a protected surface.",
            )
        locked = [span for span in active_snapshot.spans if span.locked]
        if any(span.text not in speech_text for span in locked):
            return _failure(
                "LOCKED_READING_MUTATION",
                "Critical",
                "LLM response changed a rule-engine locked reading.",
            )
        if _SEMANTIC_GUARD_RE.findall(normalized_text) != _SEMANTIC_GUARD_RE.findall(
            speech_text
        ):
            return _failure(
                "SEMANTIC_MUTATION",
                "Critical",
                "LLM response changed a negation or absence marker.",
            )
        if active_candidates and any(
            candidate.source_text not in speech_text
            and not any(output in speech_text for output in candidate.allowed_outputs)
            for candidate in active_candidates
        ):
            return _failure(
                "LEXICON_VIOLATION",
                "High",
                "LLM response used an output outside a finite pronunciation entry.",
            )
        return _failure(
            "UNEXPECTED_KOREAN_REWRITE",
            "High",
            f"Level-{stage} LLM response changed Korean text outside its whitelist.",
        )

    character_issue = _validate_new_characters(normalized_text, speech_text)
    if character_issue is not None:
        return ValidationResult(ok=False, issues=(character_issue,))

    for wrapper in _OUTPUT_WRAPPERS:
        if wrapper not in normalized_text and wrapper in speech_text:
            return _failure(
                "FORMATTING_ERROR",
                "High",
                "LLM response added an output wrapper or input tag.",
            )
    residual_span = _find_unprotected_residual_surface(speech_text, active_snapshot)
    if residual_span is not None:
        return _failure(
            "RESIDUAL_SPEECH_SURFACE",
            "Medium",
            "LLM response left a speech-target digit, English letter, or unit symbol.",
            output_start=residual_span[0],
            output_end=residual_span[1],
        )
    return ValidationResult(ok=True)


def _find_unprotected_residual_surface(
    output: str,
    snapshot: NormalizationSnapshot,
) -> tuple[int, int] | None:
    masked = output
    protected_values = {
        span.text
        for span in snapshot.spans
        if span.locked or span.protected
    }
    protected_values.update(_CONFIRMED_KBS_NEWS_RE.findall(output))
    for value in sorted(protected_values, key=len, reverse=True):
        if value:
            masked = masked.replace(value, " " * len(value))
    lines = []
    for line in masked.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if content.strip() and is_non_korean_prose_line(content):
            lines.append(" " * len(content) + line[len(content) :])
        else:
            lines.append(line)
    match = _SPEECH_TARGET_RESIDUAL_RE.search("".join(lines))
    if match is None:
        return None
    return match.start(), match.end()


def _compile_allowed_output_pattern(
    source: str,
    snapshot: NormalizationSnapshot,
    candidates: tuple[AllowedMutation, ...],
) -> re.Pattern[str]:
    locked = _non_overlapping_locked_spans(snapshot)
    candidate_by_start = {
        item.start: item
        for item in candidates
        if not any(item.start < span.normalized_end and span.normalized_start < item.end for span in locked)
    }
    locked_by_start = {span.normalized_start: span for span in locked}
    residual_by_start = {
        match.start(): match
        for match in _RESIDUAL_RUN_RE.finditer(source)
        if not any(match.start() < span.normalized_end and span.normalized_start < match.end() for span in locked)
        and not any(match.start() < item.end and item.start < match.end() for item in candidates)
    }

    parts = [r"\A"]
    cursor = 0
    while cursor < len(source):
        locked_span = locked_by_start.get(cursor)
        if locked_span is not None:
            parts.append(re.escape(locked_span.text))
            cursor = locked_span.normalized_end
            continue
        candidate = candidate_by_start.get(cursor)
        if candidate is not None:
            variants = (candidate.source_text,) + candidate.allowed_outputs
            parts.append("(?:" + "|".join(re.escape(value) for value in dict.fromkeys(variants)) + ")")
            cursor = candidate.end
            continue
        residual = residual_by_start.get(cursor)
        if residual is not None:
            parts.append(_residual_output_pattern(residual.group(0)))
            cursor = residual.end()
            continue
        character = source[cursor]
        if character in " \t" or _SPECIAL_SPACE_RE.fullmatch(character):
            parts.append(r"[ \t,]*")
        else:
            parts.append(re.escape(character))
        cursor += 1
    parts.append(r"\Z")
    return re.compile("".join(parts))


def _residual_output_pattern(raw: str) -> str:
    time_match = _COLON_TIME_RE.fullmatch(raw)
    if time_match is not None:
        hour = int(time_match.group("hour"))
        minute = int(time_match.group("minute"))
        if is_valid_time(hour, minute):
            return re.escape(time_number_reading(hour, minute)) + " ?"

    parts: list[str] = []
    cursor = 0
    for match in _NUMERIC_CORE_RE.finditer(raw):
        if match.start() > cursor:
            parts.append(_RESIDUAL_OUTPUT_PATTERN)
        variants = _number_reading_variants(match.group(0))
        if variants:
            parts.append(
                "(?:"
                + "|".join(re.escape(value) for value in dict.fromkeys(variants))
                + ") ?"
            )
        else:
            parts.append(_RESIDUAL_OUTPUT_PATTERN)
        cursor = match.end()
    if cursor < len(raw):
        parts.append(_RESIDUAL_OUTPUT_PATTERN)
    return "".join(parts) or _RESIDUAL_OUTPUT_PATTERN


def _preserves_residual_numeric_meaning(
    source: str,
    output: str,
    snapshot: NormalizationSnapshot,
) -> bool:
    locked = _non_overlapping_locked_spans(snapshot)
    search_cursor = 0
    for residual in _RESIDUAL_RUN_RE.finditer(source):
        if any(
            residual.start() < span.normalized_end
            and span.normalized_start < residual.end()
            for span in locked
        ):
            continue
        raw = residual.group(0)
        time_match = _COLON_TIME_RE.fullmatch(raw)
        if time_match is not None:
            hour = int(time_match.group("hour"))
            minute = int(time_match.group("minute"))
            if is_valid_time(hour, minute):
                reading = time_number_reading(hour, minute)
                found = output.find(reading, search_cursor)
                if found < 0:
                    return False
                search_cursor = found + len(reading)
                continue
        for numeric in _NUMERIC_CORE_RE.finditer(raw):
            variants = _number_reading_variants(numeric.group(0))
            if not variants:
                continue
            preceding_source = (
                source[residual.start() - 1] if residual.start() > 0 else None
            )
            require_left_boundary = (
                numeric.start() == 0
                and (preceding_source is None or not preceding_source.isalnum())
            )
            positions = []
            for value in variants:
                position = output.find(value, search_cursor)
                while position >= 0:
                    if not require_left_boundary or position == 0 or not (
                        "가" <= output[position - 1] <= "힣"
                    ):
                        positions.append((position, value))
                        break
                    position = output.find(value, position + 1)
            if not positions:
                return False
            position, value = min(positions, key=lambda item: item[0])
            search_cursor = position + len(value)
    return True


def _number_reading_variants(raw: str) -> tuple[str, ...]:
    variants: list[str] = []
    reading = read_number_text(raw)
    if reading is not None:
        variants.append(reading)
    normalized_integer = raw.replace(",", "")
    if normalized_integer.isdigit() and not normalized_integer.startswith("0"):
        value = int(normalized_integer)
        if 1 <= value <= 99:
            native = native_number_under_100(value)
            if native is not None:
                variants.append(native)
    return tuple(dict.fromkeys(variants))


def _non_overlapping_locked_spans(snapshot: NormalizationSnapshot):
    selected = []
    for span in sorted(
        (span for span in snapshot.spans if span.locked or span.protected),
        key=lambda item: (item.normalized_start, -(item.normalized_end - item.normalized_start)),
    ):
        if any(span.normalized_start < item.normalized_end and item.normalized_start < span.normalized_end for item in selected):
            continue
        selected.append(span)
    return tuple(selected)


def _validate_new_characters(source: str, output: str) -> ValidationIssue | None:
    if _COMPATIBILITY_JAMO_RE.search(output) and not _COMPATIBILITY_JAMO_RE.search(source):
        return ValidationIssue("INVALID_UNICODE", "High", "LLM response introduced compatibility jamo.")
    if _SPECIAL_SPACE_RE.search(output) and not _SPECIAL_SPACE_RE.search(source):
        return ValidationIssue("FORMATTING_ERROR", "High", "LLM response introduced a special space.")
    if _CONTROL_RE.search(output) and not _CONTROL_RE.search(source):
        return ValidationIssue("FORMATTING_ERROR", "High", "LLM response introduced a control character.")
    if any(character in output and character not in source for character in _DISALLOWED_DASHES):
        return ValidationIssue("FORMATTING_ERROR", "High", "LLM response introduced a non-ASCII dash.")
    if "  " in output and "  " not in source:
        return ValidationIssue("FORMATTING_ERROR", "High", "LLM response introduced consecutive spaces.")
    if re.search(r"\s-|\-\s", output) and not re.search(r"\s-|\-\s", source):
        return ValidationIssue("FORMATTING_ERROR", "High", "LLM response introduced whitespace around a hyphen.")
    return None


def _failure(
    code: str,
    severity: str,
    message: str,
    *,
    output_start: int | None = None,
    output_end: int | None = None,
) -> ValidationResult:
    return ValidationResult(
        ok=False,
        issues=(
            ValidationIssue(
                code=code,
                severity=severity,
                message=message,
                output_start=output_start,
                output_end=output_end,
            ),
        ),
    )


def _adds_comma_to_stage1_leading_time_frame(
    normalized_text: str,
    speech_text: str,
) -> bool:
    source_states = _leading_time_frame_comma_states(normalized_text)
    output_states = _leading_time_frame_comma_states(speech_text)
    for source_state, output_state in zip(source_states, output_states):
        if source_state is False and output_state is True:
            return True
    return False


def _leading_time_frame_comma_states(text: str) -> list[bool | None]:
    states: list[bool | None] = []
    for start, end in _sentence_ranges(text):
        sentence = text[start:end]
        match = _LEADING_TIME_FRAME_RE.match(sentence)
        if match is None:
            states.append(None)
            continue
        cursor = match.end()
        while cursor < len(sentence) and sentence[cursor] in " \t":
            cursor += 1
        states.append(cursor < len(sentence) and sentence[cursor] == ",")
    return states


def _sentence_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0
    index = 0
    while index < len(text):
        character = text[index]
        if character == "\n":
            ranges.append((start, index + 1))
            start = index + 1
        elif character in ".!?":
            previous = text[index - 1] if index > 0 else ""
            following = text[index + 1] if index + 1 < len(text) else ""
            if (
                previous.isascii()
                and following.isascii()
                and (
                    (previous.isdigit() and following.isdigit())
                    or (previous.isalpha() and following.isalpha())
                )
            ):
                index += 1
                continue
            ranges.append((start, index + 1))
            start = index + 1
        index += 1
    if start < len(text):
        ranges.append((start, len(text)))
    return ranges


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
        structure.append(" " if _SPECIAL_SPACE_RE.fullmatch(character) else character)
    return structure
