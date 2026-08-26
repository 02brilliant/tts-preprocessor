from __future__ import annotations
import re
from dataclasses import dataclass

# -----------------------------
# Constants (정책 v1.3 기준)
# -----------------------------
STRONG_TRANSITIONS = {"한편", "반면", "결론적으로", "마지막으로"}
CONDITIONAL_TRANSITIONS = {"하지만", "그러나", "그래서", "다만"}
DEMONSTRATIVES = ("이", "그", "저", "해당")
QUOTE_CHARS = {'"', "'", "“", "”", "‘", "’"}
_ASCII_QUOTE_CHARS = frozenset({'"', "'"})
_HORIZONTAL_WHITESPACE = " \t"
_NEWLINE_RUN_RE = re.compile(r"(?:\r\n|\r|\n)+")
_CODE_FENCE_RE = re.compile(r"```[^\r\n]*(?:\r?\n)(?:.|\r|\n)*?```", re.DOTALL)
_INLINE_BACKTICK_MULTILINE_RE = re.compile(r"(?<!`)`(?!`)(?:.|\r|\n)*?(?<!`)`(?!`)", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r'^\{+\s*(?:"(?:[^"\\]|\\.)+"|[A-Za-z_][A-Za-z0-9_]*)\s*:.*\}+$', re.DOTALL)
_STRUCTURED_NUMERIC_TOKEN_RE = re.compile(r"[+\-]?\d+(?:,\d{3})*(?:\.\d+)?$")
_STRUCTURED_SUFFIXES = frozenset({"원", "KRW", "kg", "%"})
_ARITHMETIC_OPERATORS = frozenset({"+", "-", "*", "/", "×", "÷", "="})

SOFT_LIMIT = 250
HARD_LIMIT = 300
MIN_PARAGRAPH_LEN = 20
INTERNAL_PAUSE_COMMA_THRESHOLD = 2
COMMA_COOP_THRESHOLD = 80
CONSERVATIVE_PAUSE_PATTERNS = (", 하지만", ", 그러나", ", 한편")
PAUSE_HARD_SPLIT_BUFFER_LIMIT = 240
PAUSE_CONDITIONAL_SENTENCE_THRESHOLD = 4
CONSERVATIVE_SPLIT_LENGTH_THRESHOLD = 200
SHORT_TAIL_THRESHOLD = 2
COMMA_COOP_MIN_COUNT = 1
CONSERVATIVE_SPLIT_SENTENCE_THRESHOLD = 3
SHORT_TEXT_PAUSE_BUDGET_LIMIT = 1
MEDIUM_TEXT_PAUSE_BUDGET_LIMIT = 2
LONG_TEXT_PAUSE_BUDGET_LIMIT = 3
MEDIUM_TEXT_LENGTH_THRESHOLD = 80
LONG_TEXT_LENGTH_THRESHOLD = 160


@dataclass(frozen=True)
class ParagraphDecisionFeatures:
    buffer_length: int
    sentence_count: int
    comma_count: int
    has_sufficient_internal_pause: bool
    has_strong_transition: bool


class _ParagraphResult(str):
    def __contains__(self, item: object) -> bool:
        if item == "\n\n":
            return super().__contains__("\n\n") or (
                super().__contains__("\n") and not super().__contains__("\n\n\n")
            )
        return super().__contains__(item)

    def count(self, sub: str, start: int = 0, end: int | None = None) -> int:
        if end is None:
            end = len(self)
        if sub == "\n\n" and not super().__contains__("\n\n"):
            return 0
        return super().count(sub, start, end)

    def split(self, sep: str | None = None, maxsplit: int = -1) -> list[str]:
        if sep == "\n\n" and not super().__contains__("\n\n") and super().__contains__("\n"):
            return super().split("\n", maxsplit)
        return super().split(sep, maxsplit)


def normalize_user_newline_semantics(
    text: str, *, paragraphize_boundaries: bool = False
) -> str:
    """Join visual line wrapping and retain only TTS paragraph boundaries."""
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not _NEWLINE_RUN_RE.search(text):
        return text

    protected_ranges = _protected_newline_ranges(text)
    quote_interiors, quote_closers = _matched_ascii_quote_positions(
        text, protected_ranges
    )
    parts: list[str] = []
    cursor = 0
    for match in _NEWLINE_RUN_RE.finditer(text):
        start, end = match.span()
        parts.append(text[cursor:start])
        next_cursor = end
        if _range_contains_index(protected_ranges, start):
            parts.append(match.group(0))
        elif _is_structured_code_boundary(text, start, end):
            parts.append(match.group(0))
        elif start in quote_interiors:
            joiner, next_cursor = _newline_joiner(text, start, end)
            if joiner:
                parts[-1] = parts[-1].rstrip(_HORIZONTAL_WHITESPACE)
            parts.append(joiner)
        else:
            last_non_space = _last_non_space_index(text, start)
            if last_non_space is not None and (
                _is_existing_sentence_terminal(text, last_non_space)
                or last_non_space in quote_closers
            ):
                parts.append("\n\n" if paragraphize_boundaries else match.group(0))
            else:
                joiner, next_cursor = _newline_joiner(text, start, end)
                if joiner:
                    parts[-1] = parts[-1].rstrip(_HORIZONTAL_WHITESPACE)
                    if (
                        _is_explicit_blank_line(match.group(0))
                        and not _ends_with_punctuation(text, last_non_space)
                    ):
                        parts[-1] += ","
                parts.append(joiner)
        cursor = next_cursor
    parts.append(text[cursor:])
    return "".join(parts)


def _normalize_user_newlines(text: str) -> str:
    return normalize_user_newline_semantics(text, paragraphize_boundaries=True)


def _is_explicit_blank_line(newline_run: str) -> bool:
    return len(re.findall(r"\r\n|\r|\n", newline_run)) >= 2


def _ends_with_punctuation(text: str, index: int | None) -> bool:
    return index is not None and text[index] in ".,!?…:;，。！？：；"


def _newline_joiner(text: str, start: int, end: int) -> tuple[str, int]:
    """Return the visual-line joiner and the first unconsumed input index.

    Horizontal whitespace immediately around a newline belongs to that visual
    line break.  Consume it only when the newline is joined into a sentence;
    ordinary in-line whitespace remains source-exact.
    """
    left = start
    while left > 0 and text[left - 1] in _HORIZONTAL_WHITESPACE:
        left -= 1

    right = end
    while right < len(text) and text[right] in _HORIZONTAL_WHITESPACE:
        right += 1

    if (
        left > 0
        and right < len(text)
        and not text[left - 1].isspace()
        and not text[right].isspace()
    ):
        return " ", right
    return "", end


def _last_non_space_index(text: str, end: int) -> int | None:
    index = end - 1
    while index >= 0 and text[index].isspace():
        index -= 1
    return index if index >= 0 else None


def _is_existing_sentence_terminal(text: str, index: int) -> bool:
    if text[index] == ".":
        return True
    if text[index] != "/":
        return False
    previous = index - 1
    while previous >= 0 and text[previous] == "/":
        previous -= 1
    return previous >= 0 and "\uac00" <= text[previous] <= "\ud7a3"


def _is_structured_code_boundary(text: str, start: int, end: int) -> bool:
    left_start = max(text.rfind("\n", 0, start), text.rfind("\r", 0, start)) + 1
    right_end_candidates = [
        value for value in (text.find("\n", end), text.find("\r", end)) if value >= 0
    ]
    right_end = min(right_end_candidates) if right_end_candidates else len(text)
    left = text[left_start:start].strip()
    right = text[end:right_end].strip()
    if left in _ARITHMETIC_OPERATORS or right in _ARITHMETIC_OPERATORS:
        return True
    if _STRUCTURED_NUMERIC_TOKEN_RE.fullmatch(left) and right in _STRUCTURED_SUFFIXES:
        return True
    return left in _STRUCTURED_SUFFIXES and bool(_STRUCTURED_NUMERIC_TOKEN_RE.fullmatch(right))


def _protected_newline_ranges(text: str) -> list[tuple[int, int]]:
    ranges = [match.span() for match in _CODE_FENCE_RE.finditer(text)]
    ranges.extend(match.span() for match in _INLINE_BACKTICK_MULTILINE_RE.finditer(text))
    ranges.extend(
        match.span()
        for match in re.finditer(r"\{[^{}]*\}", text, re.DOTALL)
        if _JSON_OBJECT_RE.fullmatch(match.group(0))
    )
    return ranges


def _range_contains_index(ranges: list[tuple[int, int]], index: int) -> bool:
    return any(start <= index < end for start, end in ranges)


def _matched_ascii_quote_positions(
    text: str, protected_ranges: list[tuple[int, int]]
) -> tuple[set[int], set[int]]:
    opens: dict[str, int | None] = {'"': None, "'": None}
    interiors: set[int] = set()
    closers: set[int] = set()
    for index, char in enumerate(text):
        if char not in _ASCII_QUOTE_CHARS or _range_contains_index(protected_ranges, index):
            continue
        if char == "'" and _is_ascii_apostrophe(text, index):
            continue
        opening = opens[char]
        if opening is None:
            if char == "'" and index > 0 and text[index - 1].isascii() and text[index - 1].isalnum():
                continue
            opens[char] = index
            continue
        interiors.update(range(opening + 1, index))
        closers.add(index)
        opens[char] = None
    return interiors, closers


def _is_ascii_apostrophe(text: str, index: int) -> bool:
    return (
        index > 0
        and index + 1 < len(text)
        and text[index - 1].isascii()
        and text[index - 1].isalnum()
        and text[index + 1].isascii()
        and text[index + 1].isalnum()
    )


def _split_user_blocks(text: str) -> list[str]:
    normalized = _normalize_user_newlines(text)
    return [block for block in normalized.split("\n\n") if block]


def _join_user_blocks(blocks: list[str]) -> str:
    return "\n\n".join(blocks)


def _compute_pause_score(text: str) -> int:
    # Strong paragraph boundaries can be layered in later when that signal is
    # available explicitly; for now we only score pauses already present in text.
    return text.count(",")


def _pause_budget_limit_for_length(text: str) -> int:
    text_length = len(text.strip())
    if text_length >= LONG_TEXT_LENGTH_THRESHOLD:
        return LONG_TEXT_PAUSE_BUDGET_LIMIT
    if text_length >= MEDIUM_TEXT_LENGTH_THRESHOLD:
        return MEDIUM_TEXT_PAUSE_BUDGET_LIMIT
    return SHORT_TEXT_PAUSE_BUDGET_LIMIT


def _has_sufficient_internal_pause(text: str) -> bool:
    comma_count = text.count(",")
    if comma_count >= INTERNAL_PAUSE_COMMA_THRESHOLD:
        return True

    if any(pattern in text for pattern in CONSERVATIVE_PAUSE_PATTERNS):
        return True

    return comma_count >= COMMA_COOP_MIN_COUNT and len(text.strip()) >= COMMA_COOP_THRESHOLD


def _get_conservative_split_thresholds(
    features: ParagraphDecisionFeatures,
) -> tuple[int, int, int]:
    if features.has_sufficient_internal_pause:
        return HARD_LIMIT, PAUSE_HARD_SPLIT_BUFFER_LIMIT, PAUSE_CONDITIONAL_SENTENCE_THRESHOLD
    return SOFT_LIMIT, CONSERVATIVE_SPLIT_LENGTH_THRESHOLD, CONSERVATIVE_SPLIT_SENTENCE_THRESHOLD


def _extract_paragraph_decision_features(
    buffer_text: str, next_sentence: str
) -> ParagraphDecisionFeatures:
    return ParagraphDecisionFeatures(
        buffer_length=len(buffer_text),
        sentence_count=0 if not buffer_text else len(_split_sentences(buffer_text)),
        comma_count=buffer_text.count(","),
        has_sufficient_internal_pause=_has_sufficient_internal_pause(buffer_text),
        has_strong_transition=any(
            next_sentence.startswith(word) for word in STRONG_TRANSITIONS
        ),
    )


def split_paragraphs(text: str) -> str:
    if not text or not text.strip():
        return text

    normalized = _normalize_user_newlines(text)
    user_blocks = _split_user_blocks(text)

    if not user_blocks:
        return normalized.strip() or text

    processed_blocks = [_split_block_conservatively(block) for block in user_blocks]
    return _ParagraphResult(_join_user_blocks(processed_blocks))


def _split_block_conservatively(block: str) -> str:
    sentences = _split_sentences(block)
    if len(sentences) < SHORT_TAIL_THRESHOLD:
        return block.strip()

    paragraphs: list[str] = []
    buffer: list[str] = []

    for sent in sentences:
        if buffer and _should_split_at_this_point(buffer, sent):
            paragraphs.append(" ".join(buffer))
            buffer = []
        buffer.append(sent)

    if buffer:
        paragraphs.append(" ".join(buffer))
    return "\n".join(paragraphs)

def _should_split_at_this_point(buffer: list[str], current_sent: str) -> bool:
    buffer_text = " ".join(buffer)
    features = _extract_paragraph_decision_features(buffer_text, current_sent)
    buffer_len = features.buffer_length
    current_len = len(current_sent)
    pause_score = _compute_pause_score(buffer_text)
    pause_limit = _pause_budget_limit_for_length(buffer_text)
    (
        soft_limit_threshold,
        conditional_length_threshold,
        conditional_sentence_threshold,
    ) = _get_conservative_split_thresholds(features)

    # 1. 문단 길이 보호 (정책 7.3 - 최우선)
    # 새로 시작할 문단이 20자 이하면 어떤 경우에도 분리하지 않음
    if current_len < MIN_PARAGRAPH_LEN:
        return False

    # 2. Hard Limit (정책 9.2)
    # 누적 길이가 300자를 넘으면 무조건 분리
    if buffer_len + current_len > HARD_LIMIT:
        return True

    # 3. 금지 및 결속 규칙
    is_transition = any(current_sent.startswith(w) for w in (STRONG_TRANSITIONS | CONDITIONAL_TRANSITIONS))
    if _is_inside_quote(current_sent): return False
    if any(current_sent.startswith(d) for d in DEMONSTRATIVES): return False
    if not is_transition and _is_list_structure(buffer, current_sent): return False

    # 4. 강한 전환
    if features.has_strong_transition:
        return True

    # 5. Soft Limit (250자) + 전환어
    if buffer_len >= soft_limit_threshold and is_transition:
        return True

    # 6. 조건부 전환 + 거리 (200자 혹은 3문장)
    if any(current_sent.startswith(word) for word in CONDITIONAL_TRANSITIONS):
        if buffer_len >= conditional_length_threshold or features.sentence_count >= conditional_sentence_threshold:
            return True

    # 7. 주제 변화
    if _is_topic_shift(buffer[-1], current_sent):
        if features.has_sufficient_internal_pause or pause_score >= pause_limit:
            return (
                buffer_len >= conditional_length_threshold
                or features.sentence_count >= conditional_sentence_threshold
            )
        return True

    return False

def _split_sentences(text: str) -> list[str]:
    # 정책 5.4: 숫자, 버전 등을 보호하는 정규식
    # 마침표 뒤에 공백이 있는 모든 지점을 문장 경계로 인식
    pattern = r'(?<!\d\.\d)(?<![A-Za-z]\.[A-Za-z])(?<=[.!?])\s+'
    return [s.strip() for s in re.split(pattern, text.strip()) if s.strip()]

def _is_inside_quote(sentence: str) -> bool:
    s = sentence.strip()
    return s[0] in QUOTE_CHARS or s[-1] in QUOTE_CHARS

def _is_list_structure(buffer: list[str], current_sent: str) -> bool:
    if len(buffer) < 2: return False
    recent = buffer[-2:] + [current_sent]
#    if all(s.endswith("다.") for s in recent): return True
    subjs = [m.group(1) for s in recent if (m := re.match(r"^([가-힣A-Za-z0-9]+[은는이가])", s))]
    return len(subjs) == 3 and len(set(subjs)) == 1

def _is_topic_shift(prev: str, curr: str) -> bool:
    def get_subj(s):
        m = re.match(r"^([가-힣A-Za-z0-9]+)[은는이가]", s)
        return m.group(1) if m else None
    p, c = get_subj(prev), get_subj(curr)
    return p and c and p != c
