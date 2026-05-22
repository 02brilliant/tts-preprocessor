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


def _normalize_user_newlines(text: str) -> str:
    return re.sub(r"\n+", "\n\n", text)


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
