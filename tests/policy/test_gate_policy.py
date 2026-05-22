from __future__ import annotations

from engine.pipeline.transform_engine import normalize_text


def test_time_gate_policy_positive_and_negative_cases():
    positive = normalize_text("회의는 12:30에 시작한다")
    assert positive.text == "회의는 열두시 삼십분에 시작한다"
    assert any("time_colon_context:pass" in entry for entry in positive.gate_logs)

    negative = normalize_text("score 12:30")
    assert negative.text == "score 12:30"
    assert any("time_colon_context:fail" in entry for entry in negative.gate_logs)


def test_event_gate_policy_positive_and_negative_cases():
    blocked = normalize_text("12.3 비상계엄")
    assert blocked.text == "12.3 비상계엄"
    assert any("event_keyword:fail" in entry for entry in blocked.gate_logs)

    allowed = normalize_text("12.12 대책")
    assert allowed.text == "십이십이 대책"
    assert any("event_keyword:pass" in entry for entry in allowed.gate_logs)


def test_emergency_gate_policy_positive_and_negative_cases():
    positive = normalize_text("긴급번호 112는 경찰 신고 번호다")
    assert positive.text == "긴급번호 일일이는 경찰 신고 번호다"
    assert any("emergency_context:pass" in entry for entry in positive.gate_logs)

    negative = normalize_text("긴급 신고는 112번으로 한다")
    assert negative.text == "긴급 신고는 백십이번으로 한다"
    assert any("emergency_context:fail" in entry for entry in negative.gate_logs)


def test_counter_gate_policy_hybrid_and_sino_only_cases():
    hybrid = normalize_text("21명")
    assert hybrid.text == "스물한 명"
    assert any("counter_policy:pass" in entry for entry in hybrid.gate_logs)

    sino_only = normalize_text("21층")
    assert sino_only.text == "이십일 층"
    assert any("counter_policy:pass" in entry for entry in sino_only.gate_logs)
