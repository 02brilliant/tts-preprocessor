from __future__ import annotations

from dataclasses import dataclass
import re

from engine.span_engine.language_gate import is_non_korean_prose_line
from engine.span_engine.protected import protected_literal_spans
from LLM.pronunciation_lexicon import build_allowed_mutations


_HANGUL_TOKEN_RE = re.compile(r"[가-힣]+")
_WORD_RE = re.compile(r"[^\s]+")
_SENTENCE_END_RE = re.compile(r"[.!?。！？]+")
_ACTIONABLE_RESIDUE_RE = re.compile(
    r"[A-Za-z0-9]|[%‰℃℉°₩$€£¥+×÷=<>±]"
)
_CLAUSE_BOUNDARY_RE = re.compile(
    r"(?:지만|는데|으며|면서|거나|아서|어서|므로|니까|더라도|는데도|고)\s"
)
_KBS_NEWS_RE = re.compile(r"(?<![A-Za-z])KBS news(?![A-Za-z])")

# These are grammatical tails, not a pronunciation-word registry. Removing
# them prevents ordinary endings from looking like an internal compound
# boundary while retaining the noun stem for phonological inspection.
_GRAMMATICAL_TAIL_RE = re.compile(
    r"(?:"
    r"했습니다|하였습니다|합니다|됩니다|되었습니다|입니다|"
    r"이었다|이었어요|이었는데|이었지만|이에요|이어서|이세요|이셨다|"
    r"습니다|습니까|어요|아요|였다|였어요|였는데|였지만|"
    r"이라고|이라면|이라서|이며|이고|"
    r"으로는|에서는|에게는|까지는|부터는|"
    r"으로|에서|에게|까지|부터|처럼|보다|"
    r"은|는|이|가|을|를|의|에|와|과|도|만|로"
    r")+$"
)

@dataclass(frozen=True)
class LLMInvocationDecision:
    call_llm: bool
    reason: str


def decide_llm_invocation(
    normalized_text: str,
    *,
    stage_level: int,
) -> LLMInvocationDecision:
    """Decide whether an integrated level-3/4 runtime needs its LLM pass.

    The gate does not decide pronunciation. It uses residual/structure signals
    plus the closed stage-specific mutation registry to decide whether one LLM
    call can add value.
    """

    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be str")
    if isinstance(stage_level, bool) or stage_level not in {3, 4}:
        raise ValueError("stage_level must be 3 or 4")

    visible = normalized_text.strip()
    if not visible:
        return LLMInvocationDecision(False, "empty_rule_output")

    actionable_text = _mask_intentional_preserves(normalized_text)
    if _ACTIONABLE_RESIDUE_RE.search(actionable_text):
        return LLMInvocationDecision(True, "actionable_residue")

    if _has_long_compound_candidate(actionable_text):
        return LLMInvocationDecision(True, "compound_boundary_candidate")

    pronunciation_mutations = build_allowed_mutations(
        actionable_text,
        stage=stage_level,
    )
    if any(item.kind == "natural_speech_contraction" for item in pronunciation_mutations):
        return LLMInvocationDecision(True, "natural_speech_contraction_candidate")

    if pronunciation_mutations:
        return LLMInvocationDecision(True, "korean_pronunciation_candidate")

    structural_text = actionable_text.strip()
    word_count = len(_WORD_RE.findall(structural_text))
    nonspace_count = sum(not char.isspace() for char in structural_text)
    sentence_count = len(_SENTENCE_END_RE.findall(structural_text))
    has_internal_newline = "\n" in structural_text or "\r" in structural_text
    has_clause_or_list = bool(
        _CLAUSE_BOUNDARY_RE.search(structural_text)
        or structural_text.count(",") >= 1
        or structural_text.count(";") >= 1
        or structural_text.count(":") >= 1
    )

    if stage_level == 3:
        if (
            has_internal_newline
            or sentence_count > 1
            or word_count > 5
            or nonspace_count > 24
            or has_clause_or_list
        ):
            return LLMInvocationDecision(True, "prosody_or_structure_candidate")
        return LLMInvocationDecision(False, "short_simple_rule_complete")

    # Natural-speech level 4 skips only extremely short, structurally simple
    # text. Closed pronunciation candidates are handled above.
    if (
        has_internal_newline
        or sentence_count > 1
        or word_count > 2
        or nonspace_count > 12
        or has_clause_or_list
    ):
        return LLMInvocationDecision(True, "natural_speech_candidate")
    return LLMInvocationDecision(False, "very_short_simple_rule_complete")


def _mask_intentional_preserves(text: str) -> str:
    chars = list(text)
    for span in protected_literal_spans(text):
        for index in range(span.start, span.end):
            chars[index] = " "
    masked = "".join(chars)
    masked = _KBS_NEWS_RE.sub(lambda match: " " * len(match.group()), masked)

    offset = 0
    chars = list(masked)
    for line in masked.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if content.strip() and is_non_korean_prose_line(content):
            for index in range(offset, offset + len(content)):
                chars[index] = " "
        offset += len(line)
    return "".join(chars)


def _has_long_compound_candidate(text: str) -> bool:
    return any(
        len(_GRAMMATICAL_TAIL_RE.sub("", match.group())) >= 6
        for match in _HANGUL_TOKEN_RE.finditer(text)
    )


__all__ = ["LLMInvocationDecision", "decide_llm_invocation"]
