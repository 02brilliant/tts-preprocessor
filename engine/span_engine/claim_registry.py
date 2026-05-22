from __future__ import annotations

from engine.span_engine.models import (
    ClaimCollisionLog,
    ClaimedRange,
    SourceSpan,
)


def spans_overlap(left: SourceSpan, right: SourceSpan) -> bool:
    return left.start < right.end and right.start < left.end


def _same_span(left: SourceSpan, right: SourceSpan) -> bool:
    return left.start == right.start and left.end == right.end


def _contains(parent: SourceSpan, child: SourceSpan) -> bool:
    return parent.start <= child.start <= child.end <= parent.end


class SurfaceClaimRegistry:
    def __init__(self) -> None:
        self.claims: list[ClaimedRange] = []
        self.collision_logs: list[ClaimCollisionLog] = []

    def can_claim(self, span: SourceSpan, owner: str) -> bool:
        self._validate_can_claim_args(span, owner)
        return self._blocking_claim(span, owner) is None

    def claim(self, claim: ClaimedRange) -> None:
        if not isinstance(claim, ClaimedRange):
            raise TypeError("claim must be ClaimedRange")
        blocker = self._blocking_claim(claim.span, claim.owner)
        if blocker is not None:
            log = self._make_collision_log(claim, blocker)
            self.collision_logs.append(log)
            raise ValueError(log.reason)
        self.claims.append(claim)

    def find_overlaps(self, span: SourceSpan) -> list[ClaimedRange]:
        if not isinstance(span, SourceSpan):
            raise TypeError("span must be SourceSpan")
        return [claim for claim in self.claims if spans_overlap(claim.span, span)]

    def is_blocked(self, span: SourceSpan) -> bool:
        if not isinstance(span, SourceSpan):
            raise TypeError("span must be SourceSpan")
        return any(
            spans_overlap(claim.span, span) and not claim.reentry_allowed
            for claim in self.claims
        )

    def _validate_can_claim_args(self, span: SourceSpan, owner: str) -> None:
        if not isinstance(span, SourceSpan):
            raise TypeError("span must be SourceSpan")
        if not isinstance(owner, str):
            raise TypeError("owner must be str")

    def _blocking_claim(self, span: SourceSpan, owner: str) -> ClaimedRange | None:
        for existing in self.find_overlaps(span):
            if _same_span(existing.span, span):
                return existing
            if existing.reentry_allowed and _contains(existing.span, span):
                continue
            if existing.reentry_allowed:
                return existing
            return existing
        return None

    def _make_collision_log(
        self, attempted: ClaimedRange, existing: ClaimedRange
    ) -> ClaimCollisionLog:
        return ClaimCollisionLog(
            attempted_owner=attempted.owner,
            attempted_span=attempted.span,
            existing_owner=existing.owner,
            existing_span=existing.span,
            reason=_collision_reason(existing),
            metadata={
                "attempted_claim_type": attempted.claim_type,
                "existing_claim_type": existing.claim_type,
            },
        )


def _collision_reason(existing: ClaimedRange) -> str:
    if existing.claim_type == "preserve":
        return "preserve_claim_blocks_reentry"
    if existing.claim_type == "gate_fail":
        return "gate_fail_claim_blocks_reentry"
    if existing.claim_type == "lock":
        return "lock_claim_blocks_reentry"
    if existing.claim_type == "shadow":
        return "shadow_claim_blocks_reentry"
    return "surface_claim_overlap"
