from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_entrypoint_module():
    path = Path("bin/build_binary_entrypoint.py").resolve()
    spec = importlib.util.spec_from_file_location("phase33c_build_binary_entrypoint", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase33c_binary_entrypoint_default_is_mode_less(monkeypatch) -> None:
    module = _load_entrypoint_module()
    monkeypatch.setattr(sys, "argv", ["tts_preprocessor", "--text", "12.3 비상계엄"])

    args = module.parse_args()

    assert args.text == "12.3 비상계엄"
    assert not hasattr(args, "rollout_mode")


def test_phase33c_api_default_path_uses_mode_less_binary_runtime(monkeypatch) -> None:
    import api.server as server

    expected = {
        "12.3 비상계엄": "십이삼 비상계엄",
        "90km/h이다": "시속 구십 킬로미터이다",
        "[3kg]": "3kg",
        "40℉abc": "40℉abc",
    }
    seen: list[str] = []

    def fake_run_transform_binary(text: str) -> str:
        seen.append(text)
        return expected[text]

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)

    for input_text, output_text in expected.items():
        assert server.transform_request_payload({"text": input_text}) == {
            "normalized_text": output_text
        }

    assert seen == list(expected)


def test_phase33c_api_server_does_not_import_engine_source_directly() -> None:
    text = Path("api/server.py").read_text(encoding="utf-8")

    assert "from api.binary_runtime import" in text
    assert "from engine." not in text
    assert "import engine." not in text


def test_phase33c_start_server_allows_binary_override_without_breaking_packaged_default() -> None:
    text = Path("scripts/start_server.sh").read_text(encoding="utf-8")

    assert "TTS_PREPROCESSOR_BINARY:-" in text
    assert "LATEST_BINARY=" in text
    assert "packages/tts-preprocessor/tts-preprocessor" in text
    assert "TTS_PREPROCESSOR_BINARY=" in text


def test_phase33c_removed_rollout_payload_is_rejected() -> None:
    import api.server as server

    with pytest.raises(ValueError, match="not supported"):
        server.transform_request_payload(
            {"text": "AI", "rollout_mode": "span_default"}
        )
