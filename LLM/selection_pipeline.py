from __future__ import annotations

from dataclasses import dataclass
import json
import re

from LLM.pronunciation_lexicon import build_allowed_mutations
from LLM.provenance import minimal_snapshot
from LLM.validation_models import AllowedMutation, NormalizationSnapshot


_PROSODY_SPACE_RE = re.compile(r"(?<=[가-힣]) (?=[가-힣])")
_SENTENCE_END_RE = re.compile(r"[.!?。！？]+")
_WORD_RE = re.compile(r"[^\s]+")
_HANGUL_WORD_BEFORE_SPACE_RE = re.compile(r"[가-힣]+$")
_STAGE3_CLAUSE_ENDINGS = (
    "지만",
    "는데",
    "으며",
    "면서",
    "거나",
    "아서",
    "어서",
    "므로",
    "니까",
    "더라도",
    "는데도",
    "고",
)
_MAX_SELECTION_CANDIDATES = 96

_GENERIC_GUIDANCE = {
    "natural_speech_contraction": (
        "문체와 발화 자연성을 고려해 이다 계열 축약을 선택한다. "
        "불확실하면 선택하지 않는다."
    ),
    "locked_natural_speech_contraction": (
        "확정 발음형을 보존해 코드가 계산한 이다 계열 결합 축약이다. "
        "자연스러울 때만 선택한다."
    ),
    "compound_boundary": (
        "긴 복합명사의 의미 경계가 명확하고 TTS 오독 방지에 필요할 때만 "
        "하이픈 후보 하나를 선택한다."
    ),
    "prosody_comma": (
        "긴 문장의 호흡과 의미 단위가 명확할 때만 쉼표를 선택한다. "
        "관형어-명사, 목적어-서술어, 조사·어미 앞은 선택하지 않는다."
    ),
    "residual_acronym": "일반 발화 약어일 때 글자 이름 읽기를 선택한다.",
    "residual_number": "식별자가 아닌 일반 수량일 때 코드가 계산한 읽기를 선택한다.",
    "residual_counter": (
        "문맥으로 번호·순서·점수·시간은 한자 수사, 실제 수량·높임 사람 수는 "
        "고유어 수사를 선택한다. 분은 시간/사람, 점은 점수/물건, 조는 큰 수/조 "
        "편성을 구분한다. 불확실하면 생략한다."
    ),
    "residual_ratio_or_time": (
        "비율·점수이면 대 읽기, 시각이면 시·분 읽기를 선택한다. "
        "코드·식별자이거나 불확실하면 생략한다."
    ),
    "residual_fraction": (
        "수학적 분수임이 확실할 때만 분의 읽기를 선택한다. "
        "날짜·경로·식별자이거나 불확실하면 생략한다."
    ),
    "deferred_n_beon": (
        "버스·문항·창구·후보 같은 식별 대상이면 한자 수사, 반복·확인·시도·처리 "
        "같은 동작의 횟수이면 고유어 수사를 선택한다. 조사 없이 'N번 + 동작 서술어'가 "
        "이어지면 횟수를 우선하고, 'N번 항목'이나 '대상 N번을 처리'처럼 번호 대상이 "
        "명시되면 번호를 선택한다. 그래도 불확실하면 선택하지 않는다."
    ),
}


class SelectionResponseError(ValueError):
    """The model returned an invalid or unauthorized selection document."""


@dataclass(frozen=True)
class SelectionCandidate:
    candidate_id: str
    start: int
    end: int
    kind: str
    surface: str
    options: tuple[str, ...]
    guidance: str
    source: str | None = None
    required: bool = False

    def to_payload(self) -> dict:
        return {
            "id": self.candidate_id,
            "span": [self.start, self.end],
            "kind": self.kind,
            "surface": self.surface,
            "options": list(self.options),
            "required": self.required,
            "guidance": self.guidance,
            "source": self.source,
        }

    def to_allowed_mutation(self) -> AllowedMutation:
        return AllowedMutation(
            start=self.start,
            end=self.end,
            source_text=self.surface,
            allowed_outputs=self.options,
            kind=self.kind,
        )


@dataclass(frozen=True)
class SelectionPlan:
    candidates: tuple[SelectionCandidate, ...] = ()
    stage: int | None = None

    @property
    def has_candidates(self) -> bool:
        return bool(self.candidates)

    def to_prompt_json(self) -> str:
        return json.dumps(
            {
                "schema_version": 1,
                "policy": (
                    "변경할 후보만 decisions에 넣는다. option은 options 배열의 0 기반 "
                    "인덱스다. options가 하나면 유효한 option은 0뿐이다. required 후보는 "
                    "반드시 선택하고 불확실한 선택 후보는 생략한다."
                ),
                "candidates": [candidate.to_payload() for candidate in self.candidates],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def to_allowed_mutations(self) -> tuple[AllowedMutation, ...]:
        return tuple(candidate.to_allowed_mutation() for candidate in self.candidates)

    def validate_for_text(self, text: str, *, stage: int) -> None:
        if stage not in {3, 4, 5}:
            raise ValueError("selection stage must be 3, 4, or 5")
        if self.stage is not None and self.stage != stage:
            raise ValueError("selection plan belongs to another stage")
        expected_prefix = f"S{stage}-"
        seen: set[str] = set()
        for candidate in self.candidates:
            if candidate.candidate_id in seen:
                raise ValueError("selection plan contains a duplicate candidate id")
            if not candidate.candidate_id.startswith(expected_prefix):
                raise ValueError("selection candidate id does not match its stage")
            if (
                candidate.start < 0
                or candidate.end <= candidate.start
                or candidate.end > len(text)
                or text[candidate.start : candidate.end] != candidate.surface
            ):
                raise ValueError("selection candidate does not match source text")
            if not candidate.options or any(
                not isinstance(option, str) or not option
                for option in candidate.options
            ):
                raise ValueError("selection candidate options are invalid")
            seen.add(candidate.candidate_id)

    def for_span(self, start: int, end: int) -> SelectionPlan:
        if isinstance(start, bool) or isinstance(end, bool):
            raise TypeError("start and end must be integers")
        if not isinstance(start, int) or not isinstance(end, int):
            raise TypeError("start and end must be integers")
        if start < 0 or end < start:
            raise ValueError("invalid selection-plan span")
        return SelectionPlan(
            tuple(
                SelectionCandidate(
                    candidate_id=candidate.candidate_id,
                    start=candidate.start - start,
                    end=candidate.end - start,
                    kind=candidate.kind,
                    surface=candidate.surface,
                    options=candidate.options,
                    guidance=candidate.guidance,
                    source=candidate.source,
                    required=candidate.required,
                )
                for candidate in self.candidates
                if start <= candidate.start and candidate.end <= end
            ),
            stage=self.stage,
        )


@dataclass(frozen=True)
class SelectionDecision:
    candidate_id: str
    option: int


def build_selection_plan(
    text: str,
    *,
    stage: int,
    snapshot: NormalizationSnapshot | None = None,
) -> SelectionPlan:
    """Build finite, code-renderable choices for levels 3–5."""

    if not isinstance(text, str):
        raise TypeError("text must be str")
    if stage not in {3, 4, 5}:
        raise ValueError("selection stage must be 3, 4, or 5")
    active_snapshot = snapshot or minimal_snapshot(text)
    if active_snapshot.normalized_text != text:
        raise ValueError("snapshot does not match selection text")

    mutations = list(
        build_allowed_mutations(text, stage=stage, snapshot=active_snapshot)
    )
    if stage >= 4:
        mutations.extend(_locked_contraction_mutations(text, active_snapshot, mutations))
    from LLM.residual_preprocessor import residual_choices

    residual, occupied = residual_choices(text, active_snapshot)
    mutations.extend(residual)

    candidates: list[SelectionCandidate] = []
    contextual = _stage5_contextual_entries() if stage == 5 else {}
    for mutation in sorted(mutations, key=lambda item: (item.start, item.end)):
        entry = contextual.get(mutation.source_text)
        if entry is None and mutation.kind == "contextual_standard_pronunciation":
            entry = next(
                (
                    item
                    for surface, item in contextual.items()
                    if mutation.source_text.startswith(surface)
                ),
                None,
            )
        kind = mutation.kind
        if kind == "natural_speech_contraction" and any(
            "-" in option for option in mutation.allowed_outputs
        ):
            kind = "compound_boundary_or_natural_speech_contraction"
        guidance = (
            entry.sense_hint
            if entry is not None
            else _GENERIC_GUIDANCE.get(
                kind,
                "문맥상 확실할 때만 허용된 후보를 선택하고 불확실하면 유지한다.",
            )
        )
        candidates.append(
            SelectionCandidate(
                candidate_id="",
                start=mutation.start,
                end=mutation.end,
                kind=kind,
                surface=mutation.source_text,
                options=mutation.allowed_outputs,
                guidance=guidance,
                source=None if entry is None else entry.source,
                required=kind == "residual_structured",
            )
        )
        occupied.append((mutation.start, mutation.end))

    remaining = _MAX_SELECTION_CANDIDATES - len(candidates)
    needs_prosody = _needs_prosody_candidates(text)
    if stage == 3:
        needs_prosody = len(_WORD_RE.findall(text)) > 5 or sum(not c.isspace() for c in text) > 24 or "\n" in text
    if remaining > 0 and needs_prosody:
        positions = _prosody_positions(text, active_snapshot, occupied)
        if stage == 3:
            positions = [
                start
                for start in positions
                if _is_stage3_clause_boundary(text, start)
            ]
        for start in positions[:remaining]:
            candidates.append(
                SelectionCandidate(
                    candidate_id="",
                    start=start,
                    end=start + 1,
                    kind="prosody_comma",
                    surface=" ",
                    options=(", ",),
                    guidance=_GENERIC_GUIDANCE["prosody_comma"],
                )
            )

    prefix = f"S{stage}"
    ordered = sorted(candidates, key=lambda item: (item.start, item.end, item.kind))
    return SelectionPlan(
        tuple(
            SelectionCandidate(
                candidate_id=f"{prefix}-{index:04d}",
                start=candidate.start,
                end=candidate.end,
                kind=candidate.kind,
                surface=candidate.surface,
                options=candidate.options,
                guidance=candidate.guidance,
                source=candidate.source,
                required=candidate.required,
            )
            for index, candidate in enumerate(ordered, start=1)
        ),
        stage=stage,
    )


def parse_selection_response(
    response_text: str,
    *,
    plan: SelectionPlan,
) -> tuple[SelectionDecision, ...]:
    if not isinstance(response_text, str) or not response_text.strip():
        raise SelectionResponseError("LLM selection response is empty.")
    try:
        payload = json.loads(response_text, object_pairs_hook=_strict_json_object)
    except json.JSONDecodeError as exc:
        raise SelectionResponseError(
            "LLM selection response must be one JSON object."
        ) from exc
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "decisions"}:
        raise SelectionResponseError("LLM selection response fields are invalid.")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise SelectionResponseError("LLM selection schema_version must be 1.")
    raw_decisions = payload["decisions"]
    if not isinstance(raw_decisions, list):
        raise SelectionResponseError("LLM selection decisions must be a list.")

    candidates = {candidate.candidate_id: candidate for candidate in plan.candidates}
    decisions: list[SelectionDecision] = []
    seen: set[str] = set()
    for raw in raw_decisions:
        if not isinstance(raw, dict) or set(raw) != {"id", "option"}:
            raise SelectionResponseError("LLM selection decision fields are invalid.")
        candidate_id = raw["id"]
        option = raw["option"]
        if not isinstance(candidate_id, str) or candidate_id not in candidates:
            raise SelectionResponseError("LLM selected an unknown candidate id.")
        if candidate_id in seen:
            raise SelectionResponseError("LLM selected a candidate more than once.")
        if isinstance(option, bool) or not isinstance(option, int):
            raise SelectionResponseError("LLM selection option must be an integer.")
        if option < 0 or option >= len(candidates[candidate_id].options):
            raise SelectionResponseError("LLM selected an out-of-range option.")
        seen.add(candidate_id)
        decisions.append(SelectionDecision(candidate_id, option))

    missing_required = {
        candidate.candidate_id
        for candidate in plan.candidates
        if candidate.required and candidate.candidate_id not in seen
    }
    if missing_required:
        raise SelectionResponseError("LLM omitted a required speech-reading candidate.")
    return tuple(decisions)


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SelectionResponseError(
                "LLM selection response contains a duplicate JSON field."
            )
        result[key] = value
    return result


def recover_selection_response(
    response_text: str, *, plan: SelectionPlan,
) -> tuple[tuple[SelectionDecision, ...], bool]:
    """Recover independent decisions only from an unambiguous JSON envelope.

    Never extract prose, fenced JSON, truncated JSON, or model-provided text.
    Duplicate IDs and overlapping decisions invalidate every conflicting edit.
    """
    try:
        payload = json.loads(response_text, object_pairs_hook=_strict_json_object)
    except (ValueError, TypeError):
        return (), True
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "decisions"}
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
        or not isinstance(payload["decisions"], list)
    ):
        return (), True
    counts: dict[str, int] = {}
    for raw in payload["decisions"]:
        if isinstance(raw, dict) and isinstance(raw.get("id"), str):
            counts[raw["id"]] = counts.get(raw["id"], 0) + 1
    optional_plan = SelectionPlan(tuple(
        SelectionCandidate(c.candidate_id, c.start, c.end, c.kind, c.surface,
                           c.options, c.guidance, c.source, False)
        for c in plan.candidates
    ), stage=plan.stage)
    accepted = []
    rejected = False
    for raw in payload["decisions"]:
        try:
            decisions = parse_selection_response(json.dumps({
                "schema_version": 1, "decisions": [raw],
            }), plan=optional_plan)
            decision = decisions[0]
            if counts[decision.candidate_id] != 1:
                raise SelectionResponseError("Duplicate candidate.")
            accepted.append(decision)
        except SelectionResponseError:
            rejected = True
    by_id = {c.candidate_id: c for c in plan.candidates}
    conflicts = set()
    for index, decision in enumerate(accepted):
        a = by_id[decision.candidate_id]
        for other in accepted[index + 1:]:
            b = by_id[other.candidate_id]
            if a.start < b.end and b.start < a.end:
                conflicts.update((a.candidate_id, b.candidate_id))
    accepted = tuple(d for d in accepted if d.candidate_id not in conflicts)
    selected = {d.candidate_id for d in accepted}
    rejected |= bool(conflicts) or any(
        c.required and c.candidate_id not in selected for c in plan.candidates
    )
    return accepted, rejected


def compose_selection(
    source_text: str,
    *,
    plan: SelectionPlan,
    decisions: tuple[SelectionDecision, ...],
) -> str:
    candidates = {candidate.candidate_id: candidate for candidate in plan.candidates}
    selected = [candidates[decision.candidate_id] for decision in decisions]
    for index, candidate in enumerate(selected):
        if source_text[candidate.start : candidate.end] != candidate.surface:
            raise SelectionResponseError("Selection candidate no longer matches source text.")
        if any(
            candidate.start < other.end and other.start < candidate.end
            for other in selected[index + 1 :]
        ):
            raise SelectionResponseError("LLM selected overlapping candidates.")

    decision_by_id = {decision.candidate_id: decision for decision in decisions}
    output = source_text
    for candidate in sorted(selected, key=lambda item: item.start, reverse=True):
        decision = decision_by_id[candidate.candidate_id]
        replacement = candidate.options[decision.option]
        output = output[: candidate.start] + replacement + output[candidate.end :]
    return output


def render_selection_response(
    source_text: str,
    *,
    plan: SelectionPlan,
    response_text: str,
) -> str:
    decisions = parse_selection_response(response_text, plan=plan)
    return compose_selection(source_text, plan=plan, decisions=decisions)


def _locked_contraction_mutations(
    text: str,
    snapshot: NormalizationSnapshot,
    existing: list[AllowedMutation],
) -> list[AllowedMutation]:
    locked = tuple(span for span in snapshot.spans if span.locked)
    protected = tuple(span for span in snapshot.spans if span.protected)
    existing_keys = {(item.start, item.end) for item in existing}
    results: list[AllowedMutation] = []
    for mutation in build_allowed_mutations(text, stage=4):
        if mutation.kind != "natural_speech_contraction":
            continue
        if (mutation.start, mutation.end) in existing_keys:
            continue
        if not any(
            mutation.start < span.normalized_end
            and span.normalized_start < mutation.end
            for span in locked
        ):
            continue
        if any(
            mutation.start < span.normalized_end
            and span.normalized_start < mutation.end
            for span in protected
        ):
            continue
        results.append(
            AllowedMutation(
                start=mutation.start,
                end=mutation.end,
                kind="locked_natural_speech_contraction",
                source_text=mutation.source_text,
                allowed_outputs=mutation.allowed_outputs,
            )
        )
    return results


def _stage5_contextual_entries() -> dict[str, object]:
    # Keep level 4 independent from the level-5 data asset. Importing the
    # registry at module load would make the level-4 frozen executable require
    # stage5_pronunciations.json even though it never uses those entries.
    from LLM.standard_pronunciation import entries_for_mode

    return {entry.surface: entry for entry in entries_for_mode("contextual")}




def _needs_prosody_candidates(text: str) -> bool:
    visible = text.strip()
    return bool(
        "\n" in visible
        or "\r" in visible
        or len(_SENTENCE_END_RE.findall(visible)) > 1
        or len(_WORD_RE.findall(visible)) > 2
        or sum(not character.isspace() for character in visible) > 12
    )


def _is_stage3_clause_boundary(text: str, space_index: int) -> bool:
    match = _HANGUL_WORD_BEFORE_SPACE_RE.search(text[:space_index])
    return bool(
        match
        and any(match.group().endswith(ending) for ending in _STAGE3_CLAUSE_ENDINGS)
    )


def _prosody_positions(
    text: str,
    snapshot: NormalizationSnapshot,
    occupied: list[tuple[int, int]],
) -> list[int]:
    blocked = tuple(
        (span.normalized_start, span.normalized_end)
        for span in snapshot.spans
        if span.locked or span.protected
    )
    positions: list[int] = []
    from LLM.response_validation import is_safe_prosody_comma_insertion

    for match in _PROSODY_SPACE_RE.finditer(text):
        start = match.start()
        if _overlaps(start, start + 1, blocked + tuple(occupied)):
            continue
        if not is_safe_prosody_comma_insertion(text, start):
            continue
        positions.append(start)
    return positions


def _overlaps(start: int, end: int, spans: tuple[tuple[int, int], ...]) -> bool:
    return any(start < span_end and span_start < end for span_start, span_end in spans)


__all__ = [
    "SelectionCandidate",
    "SelectionDecision",
    "SelectionPlan",
    "SelectionResponseError",
    "build_selection_plan",
    "compose_selection",
    "parse_selection_response",
    "render_selection_response",
]
