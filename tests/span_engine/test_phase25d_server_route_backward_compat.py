from __future__ import annotations

import api.server as server


def test_phase25d_current_server_helper_compatibility_still_works(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "run_transform_binary_with_rollout",
        lambda text, rollout_mode="legacy_default", include_debug=False: {
            "ok": True,
            "mode": rollout_mode,
            "normalized_text": "시속 구십 킬로미터",
        },
    )

    result = server.transform_request_payload({"text": "90km/h", "rollout_mode": "span_default"})

    assert result["normalized_text"] == "시속 구십 킬로미터"

