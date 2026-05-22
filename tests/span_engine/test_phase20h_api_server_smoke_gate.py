from __future__ import annotations

import api.server as server
from engine.api_interface import normalize_text_with_rollout


def test_phase20h_api_helper_smoke_remains_span_default_ready() -> None:
    assert normalize_text_with_rollout(
        "90km/h",
        mode="span_default",
        legacy_transform=lambda text: text,
    ) == "시속 구십 킬로미터"


def test_phase20h_server_helper_smoke_can_be_monkeypatched(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "run_transform_binary_with_rollout",
        lambda text, rollout_mode="legacy_default", include_debug=False: {
            "ok": True,
            "mode": rollout_mode,
            "normalized_text": "시속 구십 킬로미터",
        },
    )

    result = server.transform_request_payload(
        {"text": "90km/h", "rollout_mode": "span_default"},
    )

    assert result["normalized_text"] == "시속 구십 킬로미터"
    assert result["mode"] == "span_default"
