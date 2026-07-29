from __future__ import annotations

import inspect

import pytest

from api.server import TransformRequest
from engine.main import transform, transform_debug
from engine.span_engine.claim_registry import SurfaceClaimRegistry
from engine.span_engine.models import (
    ContextualDecision,
    ContextualDecisionKind,
    ClaimedRange,
    SourceSpan,
    TransformTrace,
)
from engine.span_engine.trace import trace_to_dict


def test_contextual_decision_has_four_typed_outcomes() -> None:
    assert {kind.value for kind in ContextualDecisionKind} == {
        "confirmed",
        "deferred",
        "absolute_preserve",
        "not_applicable",
    }
    decision = ContextualDecision(
        rule_version="contextual-number-unit-v1",
        unit="번",
        decision=ContextualDecisionKind.DEFERRED,
        semantic_type="occurrence_or_identifier",
        candidate_readings=(
            {"reading": "세 번", "semantic_type": "occurrence"},
            {"reading": "삼번", "semantic_type": "identifier"},
        ),
        matched_anchor=None,
        blocking_reason="exact_anchor_missing",
        owner_priority=70,
        reentry_blocked=True,
    )
    assert decision.reentry_blocked is True


def test_contextual_trace_is_separate_from_preservation_shadow() -> None:
    trace = TransformTrace()
    trace.shadow_logs.append({"event": "shadow_unit_created"})
    trace.contextual_decision_logs.append({"unit": "번", "decision": "deferred"})

    payload = trace_to_dict(trace)

    assert payload["shadow_logs"] == [{"event": "shadow_unit_created"}]
    assert payload["contextual_decision_logs"] == [
        {"unit": "번", "decision": "deferred"}
    ]


@pytest.mark.parametrize("claim_type", ["surface", "preserve"])
def test_contextual_claim_blocks_generic_reentry(claim_type: str) -> None:
    registry = SurfaceClaimRegistry()
    contextual_span = SourceSpan(0, 2)
    registry.claim(
        ClaimedRange(
            span=contextual_span,
            owner="contextual_number_unit",
            claim_type=claim_type,
            surface_type="CONTEXTUAL_NUMBER_UNIT_SURFACE",
            reason="contextual_decision_terminal",
        )
    )

    assert registry.can_claim(SourceSpan(0, 1), "number") is False
    assert registry.can_claim(contextual_span, "numeric_suffix") is False
    assert registry.can_claim(SourceSpan(0, 1), "counter_noun") is False


def test_production_facade_and_api_remain_mode_less() -> None:
    assert "rollout_mode" not in inspect.signature(transform).parameters
    assert "rollout_mode" not in inspect.signature(transform_debug).parameters
    assert "rollout_mode" not in TransformRequest.model_fields
    with pytest.raises(ValueError):
        TransformRequest.model_validate({"text": "3번", "rollout_mode": "legacy"})
