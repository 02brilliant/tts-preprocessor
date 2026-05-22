from __future__ import annotations

import contextlib
import contextvars
from collections.abc import Callable

from .counter_gate import evaluate_counter_policy
from .emergency_gate import evaluate_emergency_context
from .event_gate import evaluate_event_keyword
from .generic_gate import (
    evaluate_decimal_context,
    evaluate_exact_text,
    evaluate_no_preceding_ascii_alpha,
    evaluate_slash_date_context,
    evaluate_slash_fraction_context,
    evaluate_unit_context,
)
from .hyphen_gate import evaluate_hyphen_digit_blocks, evaluate_hyphen_phone
from .models import GateDecision
from .time_gate import evaluate_hour_korean, evaluate_time_colon


GateEvaluator = Callable[..., GateDecision]

_ACTIVE_GATE_LOGS: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "tts_preprocessor_active_gate_logs",
    default=None,
)


class GateRegistry:
    def __init__(self) -> None:
        self._gates: dict[str, GateEvaluator] = {
            "time_colon_context": evaluate_time_colon,
            "time_hour_korean_context": evaluate_hour_korean,
            "event_keyword": evaluate_event_keyword,
            "emergency_context": evaluate_emergency_context,
            "counter_policy": evaluate_counter_policy,
            "hyphen_digit_block_routing": evaluate_hyphen_digit_blocks,
            "hyphen_phone_routing": evaluate_hyphen_phone,
            "decimal_context": evaluate_decimal_context,
            "unit_context": evaluate_unit_context,
            "exact_text": evaluate_exact_text,
            "no_preceding_ascii_alpha": evaluate_no_preceding_ascii_alpha,
            "slash_date_context": evaluate_slash_date_context,
            "slash_fraction_context": evaluate_slash_fraction_context,
        }

    def evaluate(self, gate_name: str, *, gate_logs: list[str] | None = None, **kwargs: object) -> GateDecision:
        if gate_name not in self._gates:
            raise KeyError(f"unknown gate: {gate_name}")
        decision = self._gates[gate_name](**kwargs)
        active_logs = gate_logs if gate_logs is not None else _ACTIVE_GATE_LOGS.get()
        if active_logs is not None:
            candidate = kwargs.get("candidate", "")
            status = "pass" if decision.allowed else "fail"
            detail = ", ".join(f"{key}={value}" for key, value in sorted(decision.metadata.items()))
            suffix = f" ({detail})" if detail else ""
            active_logs.append(f"{gate_name}:{status}:{decision.reason}{suffix}: {candidate!r}")
        return decision


@contextlib.contextmanager
def gate_log_scope(gate_logs: list[str]):
    token = _ACTIVE_GATE_LOGS.set(gate_logs)
    try:
        yield
    finally:
        _ACTIVE_GATE_LOGS.reset(token)


GATE_REGISTRY = GateRegistry()
