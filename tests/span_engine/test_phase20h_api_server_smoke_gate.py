from __future__ import annotations

import api.server as server
from engine.api_interface import normalize_text


def test_phase20h_api_helper_smoke_uses_canonical_facade() -> None:
    assert normalize_text("90km/h") == "시속 구십 킬로미터"


def test_phase20h_server_helper_smoke_can_be_monkeypatched(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "run_transform_binary",
        lambda text: "시속 구십 킬로미터",
    )

    result = server.transform_request_payload({"text": "90km/h"})

    assert result == {"normalized_text": "시속 구십 킬로미터"}
