from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class GateDecision:
    allowed: bool
    reason: str
    metadata: dict[str, str] = field(default_factory=dict)


def allow(reason: str, **metadata: str) -> GateDecision:
    return GateDecision(True, reason, dict(metadata))


def deny(reason: str, **metadata: str) -> GateDecision:
    return GateDecision(False, reason, dict(metadata))
