"""Ordinary API / facade responses must not expose decision debug surfaces.

Policy: contextual_decision_logs and related markers are only for
transform_debug, packaged --include-debug, and API include_debug=true.
"""

from __future__ import annotations

import pytest

from api import server as server_module
from engine.main import transform, transform_debug


FORBIDDEN_ORDINARY_KEYS = frozenset(
    {
        "contextual_decision_logs",
        "shadow_logs",
        "debug",
        "trace",
        "decision_markers",
        "candidates",
        "candidate_readings",
    }
)

LEVEL_3_4_ALLOWED_KEYS = frozenset(
    {
        "normalized_text",
        "speech_text",
        "model",
        "elapsed_ms",
        "rule_elapsed_ms",
        "llm_elapsed_ms",
        "llm_called",
        "llm_skip_reason",
        "rejected_speech_text",
        "validation_failure",
    }
)


def _assert_no_forbidden_keys(payload: dict) -> None:
    assert FORBIDDEN_ORDINARY_KEYS.isdisjoint(payload.keys())


@pytest.mark.parametrize("level", (0, 1, 2))
def test_ordinary_level_0_to_2_response_excludes_decision_debug(
    level: int, monkeypatch
) -> None:
    monkeypatch.setattr(
        server_module,
        "run_integrated_binary",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    monkeypatch.setattr(
        server_module,
        "run_transform_binary",
        lambda text, **kwargs: f"{kwargs.get('profile', 'default')}:{text}",
    )
    monkeypatch.setattr(
        server_module,
        "run_transform_binary_debug",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("debug path")),
    )

    payload = server_module.transform_request_payload(
        {"text": "3번 확인", "level": level}
    )

    assert set(payload.keys()) == {"normalized_text"}
    _assert_no_forbidden_keys(payload)
    assert "contextual_decision_logs" not in str(payload)


def test_ordinary_level_2_includes_only_normalized_text(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "run_transform_binary",
        lambda text, **_kwargs: "세-번 확인",
    )
    payload = server_module.transform_request_payload({"text": "3번 확인"})
    assert payload == {"normalized_text": "세-번 확인"}
    _assert_no_forbidden_keys(payload)


@pytest.mark.parametrize("level", (3, 4))
def test_ordinary_level_3_4_response_excludes_decision_debug(
    level: int, monkeypatch
) -> None:
    def fake_run(text, *, level, model=None):
        return {
            "normalized_text": "규칙 결과",
            "speech_text": "발화 결과",
            "model": model or "m",
            "elapsed_ms": 1.0,
            "rule_elapsed_ms": 2.0,
            "llm_elapsed_ms": 3.0,
            "llm_called": True,
            "llm_skip_reason": None,
            # Injected poison fields must not be forwarded by the API layer
            # when the integrated binary is mocked to return a clean payload;
            # this case asserts the ordinary contract whitelist on a typical
            # successful integrated response.
        }

    monkeypatch.setattr(server_module, "run_integrated_binary", fake_run)
    payload = server_module.transform_request_payload(
        {"text": "원문", "level": level, "model": "m"}
    )

    assert set(payload.keys()) <= LEVEL_3_4_ALLOWED_KEYS
    _assert_no_forbidden_keys(payload)


def test_include_debug_level_2_may_expose_contextual_decision_logs(
    monkeypatch,
) -> None:
    debug_payload = {
        "normalized_text": "세-번 확인",
        "debug": {
            "trace": {
                "contextual_decision_logs": [
                    {"unit": "번", "decision": "deferred"},
                ],
                "shadow_logs": [{"event": "shadow_unit_created"}],
            }
        },
    }

    monkeypatch.setattr(
        server_module,
        "run_transform_binary_debug",
        lambda text, **_kwargs: debug_payload,
    )
    payload = server_module.transform_request_payload(
        {"text": "3번 확인", "level": 2, "include_debug": True}
    )

    assert payload["normalized_text"] == "세-번 확인"
    assert payload["debug"]["trace"]["contextual_decision_logs"][0]["unit"] == "번"


@pytest.mark.parametrize("level", (3, 4))
def test_include_debug_rejected_for_llm_levels(level: int) -> None:
    with pytest.raises(ValueError, match="include_debug is supported only"):
        server_module.transform_request_payload(
            {"text": "원문", "level": level, "include_debug": True}
        )


def test_production_transform_string_excludes_decision_log_payload() -> None:
    text = "3번 확인"
    ordinary = transform(text)
    assert isinstance(ordinary, str)
    assert "contextual_decision_logs" not in ordinary
    assert "candidate_readings" not in ordinary

    debug = transform_debug(text)
    assert "normalized_text" in debug
    assert "debug" in debug
    trace = debug["debug"]["trace"]
    assert "contextual_decision_logs" in trace
    assert "shadow_logs" in trace
    assert "contextual_decision_logs" not in debug["normalized_text"]
