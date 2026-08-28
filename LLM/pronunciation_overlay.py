from __future__ import annotations

from dataclasses import dataclass

from LLM.pronunciation_lexicon import build_deterministic_pronunciation_mutations
from LLM.provenance import minimal_snapshot
from LLM.validation_models import (
    AllowedMutation,
    NormalizationSnapshot,
    NormalizedSpan,
)


@dataclass(frozen=True)
class PronunciationOverlayResult:
    text: str
    snapshot: NormalizationSnapshot
    applied_mutations: tuple[AllowedMutation, ...] = ()


def apply_pronunciation_overlay(
    normalized_text: str,
    *,
    stage: int,
    snapshot: NormalizationSnapshot | None = None,
) -> PronunciationOverlayResult:
    """Apply fixed stage-4 pronunciation entries without changing stage 2.

    The returned snapshot locks every generated pronunciation so the level-4
    LLM can add only closed natural-speech and prosodic changes around it.
    """

    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be str")
    if stage not in {3, 4}:
        raise ValueError("stage must be 3 or 4")
    active_snapshot = snapshot or minimal_snapshot(normalized_text)
    if active_snapshot.normalized_text != normalized_text:
        raise ValueError("snapshot does not match normalized_text")

    mutations = build_deterministic_pronunciation_mutations(
        normalized_text,
        stage=stage,
        snapshot=active_snapshot,
    )
    if not mutations:
        return PronunciationOverlayResult(normalized_text, active_snapshot)

    replacements = tuple(
        (mutation, mutation.allowed_outputs[0]) for mutation in mutations
    )
    output = normalized_text
    for mutation, replacement in reversed(replacements):
        output = output[: mutation.start] + replacement + output[mutation.end :]

    projected_spans: list[NormalizedSpan] = []
    for span in active_snapshot.spans:
        if any(
            mutation.start < span.normalized_end
            and span.normalized_start < mutation.end
            for mutation, _replacement in replacements
        ):
            continue
        start = _project_index(span.normalized_start, replacements)
        end = _project_index(span.normalized_end, replacements)
        projected_spans.append(
            NormalizedSpan(
                normalized_start=start,
                normalized_end=end,
                text=output[start:end],
                source_start=span.source_start,
                source_end=span.source_end,
                owner=span.owner,
                provenance=span.provenance,
                locked=span.locked,
                protected=span.protected,
            )
        )

    for mutation, replacement in replacements:
        start = _project_index(mutation.start, replacements)
        source_span = next(
            (
                span
                for span in active_snapshot.spans
                if span.normalized_start == mutation.start
                and span.normalized_end == mutation.end
            ),
            None,
        )
        projected_spans.append(
            NormalizedSpan(
                normalized_start=start,
                normalized_end=start + len(replacement),
                text=replacement,
                source_start=None if source_span is None else source_span.source_start,
                source_end=None if source_span is None else source_span.source_end,
                owner="stage4_pronunciation_overlay",
                provenance="GENERATED_STAGE4_PRONUNCIATION",
                locked=True,
                protected=False,
            )
        )

    updated_snapshot = NormalizationSnapshot(
        normalized_text=output,
        spans=tuple(
            sorted(
                projected_spans,
                key=lambda span: (span.normalized_start, span.normalized_end),
            )
        ),
    )
    return PronunciationOverlayResult(output, updated_snapshot, mutations)


def _project_index(
    index: int,
    replacements: tuple[tuple[AllowedMutation, str], ...],
) -> int:
    return index + sum(
        len(replacement) - len(mutation.source_text)
        for mutation, replacement in replacements
        if mutation.end <= index
    )


__all__ = ["PronunciationOverlayResult", "apply_pronunciation_overlay"]
