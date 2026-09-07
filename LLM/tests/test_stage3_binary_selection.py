"""Exercise the frozen CLI and HTTP contract with a deterministic local provider."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import threading

import pytest


@pytest.mark.binary_runtime
@pytest.mark.parametrize(("executable", "level"), (
    ("tts-preprocessor-llm-minimal", 3),
    ("tts-preprocessor-llm-natural", 4),
    ("tts-preprocessor-llm-standard", 5),
))
def test_frozen_llm_stages_resolve_processing_occurrence_without_llm(executable, level):
    binary = Path(__file__).resolve().parents[2] / "build/macos/dist" / executable
    if not binary.is_file():
        pytest.skip("macOS stage-3 executable has not been built")
    environment = dict(os.environ)
    environment.update(
        LOCAL_LLM_BASE_URL="http://127.0.0.1:1",
        LOCAL_LLM_TOKEN="test-only",
    )
    result = subprocess.run(
        [str(binary), "--text", "3번 처리했습니다.", "--model", "gemma4:e4b", "--json"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["level"] == level
    assert payload["normalized_text"] == "세-번 처리했습니다."
    assert payload["speech_text"] == "세-번 처리했습니다."
    assert payload["llm_called"] is False


@pytest.mark.binary_runtime
@pytest.mark.parametrize("invalid", [False, True, "partial"])
@pytest.mark.parametrize(("executable", "stage"), (
    ("tts-preprocessor-llm-minimal", 3),
    ("tts-preprocessor-llm-natural", 4),
    ("tts-preprocessor-llm-standard", 5),
))
def test_frozen_stage3_composes_selection_or_falls_back(invalid, executable, stage):
    binary = Path(__file__).resolve().parents[2] / "build/macos/dist" / executable
    if not binary.is_file():
        pytest.skip("macOS stage-3 executable has not been built")
    captured = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            captured.append(body)
            match = re.search(rf"<STAGE{stage}_WORK_PLAN>\n(.*?)\n</STAGE{stage}_WORK_PLAN>", body["prompt"], re.S)
            plan = json.loads(match.group(1))
            candidate = next(c for c in plan["candidates"] if c["kind"] == "deferred_n_beon")
            response = "임의 문자열" if invalid is True else json.dumps({
                "schema_version": 1,
                "decisions": [{"id": candidate["id"], "option": candidate["options"].index("세-번")}],
            })
            if invalid == "partial":
                payload = json.loads(response)
                payload["decisions"].append({"id": "<LOCK_0001>", "option": 0})
                response = json.dumps(payload)
            encoded = json.dumps({"response": response}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        environment = dict(os.environ)
        environment.update(LOCAL_LLM_BASE_URL=f"http://127.0.0.1:{server.server_port}", LOCAL_LLM_TOKEN="test-only")
        result = subprocess.run(
            [str(binary), "--text", "3번 맡았습니다.", "--model", "gemma4:e4b", "--json"],
            env=environment, capture_output=True, text=True, timeout=30,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["normalized_text"] == "3번 맡았습니다."
    assert payload["speech_text"] == ("3번 맡았습니다." if invalid is True else "세-번 맡았습니다.")
    assert payload["llm_called"] is True
    assert len(captured) == 1
    if invalid:
        assert payload["validation_failure"]["code"] == "INVALID_SELECTION_RESPONSE"
    else:
        assert "validation_failure" not in payload
