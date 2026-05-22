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


def test_phase33c_binary_entrypoint_default_is_current_engine(monkeypatch) -> None:
    module = _load_entrypoint_module()

    monkeypatch.setattr(sys, "argv", ["tts_preprocessor", "--text", "12.3 비상계엄"])

    args = module.parse_args()

    assert getattr(args, "rollout_mode") == "span_default"


def test_phase33c_api_default_path_uses_binary_runtime_without_rollout(monkeypatch) -> None:
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

    def fail_if_rollout_used(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("default API path must not use rollout compatibility")

    monkeypatch.setattr(server, "run_transform_binary", fake_run_transform_binary)
    monkeypatch.setattr(server, "run_transform_binary_with_rollout", fail_if_rollout_used)

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

    assert 'if [[ -n "${TTS_PREPROCESSOR_BINARY:-}" ]]' in text
    assert 'LATEST_BINARY="$TTS_PREPROCESSOR_BINARY"' in text
    assert "packages/tts-preprocessor/bin/tts_preprocessor" in text
    assert 'TTS_PREPROCESSOR_BINARY="$LATEST_BINARY"' in text


def test_phase33c_invalid_rollout_mode_still_rejected() -> None:
    from api.binary_runtime import run_transform_binary_with_rollout

    with pytest.raises(ValueError):
        run_transform_binary_with_rollout("AI", rollout_mode="invalid")
