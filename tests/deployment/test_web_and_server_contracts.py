from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_web_uses_three_exact_independent_download_targets() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    for archive_name in (
        "tts-preprocessor-linux.zip",
        "tts-preprocessor-macos.zip",
        "tts-preprocessor-windows.zip",
    ):
        assert archive_name in web
    assert "macOS Apple Silicon (arm64)" in web
    assert "DOWNLOAD_TARGETS.map(async (target)" in web
    assert "Promise.all(" in web
    assert "available: await checkDownloadAvailable(target.file)" in web
    assert "?availability=${Date.now()}" in web
    assert 'cache: "no-store"' in web
    assert "?download=${Date.now()}" in web


def test_server_health_uses_new_linux_download_url() -> None:
    check_server = Path("scripts/check_server.sh").read_text(encoding="utf-8")

    assert (
        'LINUX_DOWNLOAD_URL="http://${SERVER_HOST}:${SERVER_PORT}/downloads/'
        'tts-preprocessor-linux.zip"'
    ) in check_server
    assert (
        'MACOS_DOWNLOAD_URL="http://${SERVER_HOST}:${SERVER_PORT}/downloads/'
        'tts-preprocessor-macos.zip"'
    ) in check_server
    assert (
        'WINDOWS_DOWNLOAD_URL="http://${SERVER_HOST}:${SERVER_PORT}/downloads/'
        'tts-preprocessor-windows.zip"'
    ) in check_server
    assert (
        'check_get "Linux release download" "$LINUX_DOWNLOAD_URL"'
        in check_server
    )
    assert (
        'check_get "macOS release download" "$MACOS_DOWNLOAD_URL"'
        in check_server
    )
    assert (
        'check_optional_get "Windows release download" "$WINDOWS_DOWNLOAD_URL"'
        in check_server
    )
    assert 'LLM_MODELS_URL="http://${SERVER_HOST}:${SERVER_PORT}/api/llm/models"' in check_server
    assert 'LLM_TRANSFORM_URL="http://${SERVER_HOST}:${SERVER_PORT}/api/llm/transform"' in check_server
    assert 'check_llm_models "$LLM_MODELS_OUTPUT"' in check_server
    assert 'check_post_llm_transform "$LLM_TRANSFORM_OUTPUT"' in check_server


def test_server_health_allows_missing_optional_windows_download(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
output_file=""
url=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o)
      output_file="$2"
      shift 2
      ;;
    http://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done
if [[ "$url" == *"/downloads/tts-preprocessor-windows.zip" ]]; then
  exit 22
fi
if [[ "$url" == *"/api/llm/models" ]]; then
  printf '%s\\n' '{"models":["gemma4:31b","gemma4:26b","gemma4:e4b","gemini-3.6-flash","gemini-3.5-flash","gemini-3.5-flash-lite"],"default_model":"gemma4:e4b"}' > "$output_file"
elif [[ "$url" == *"/api/llm/transform" ]]; then
  printf '%s\\n' '{"llm_text":"LLM 배포 확인입니다.","model":"gemma4:e4b","elapsed_ms":1}' > "$output_file"
elif [[ "$url" == *"/api/transform" ]]; then
  printf '%s\\n' '{"normalized_text":"케이 원, 케이푸드, 백십이 명, 유월"}' > "$output_file"
else
  printf '%s\\n' "ok" > "$output_file"
fi
""",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = subprocess.run(
        ["/bin/bash", "scripts/check_server.sh"],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Windows release download is not currently available" in result.stdout
    assert "Server validation completed successfully" in result.stdout


def test_source_free_runtime_and_semantic_probe_contracts_remain() -> None:
    api_server = Path("api/server.py").read_text(encoding="utf-8")
    start_server = Path("scripts/start_server.sh").read_text(encoding="utf-8")
    remote_build = Path("scripts/build_remote_package.sh").read_text(encoding="utf-8")

    assert "from api.binary_runtime import" in api_server
    assert "from engine" not in api_server
    assert 'app.mount("/downloads"' in api_server
    assert 'TTS_PREPROCESSOR_BINARY="$LATEST_BINARY"' in start_server
    assert 'LLM_ENV_FILE="${TTS_LLM_ENV_FILE:-$BASE_DIR/config/llm.env}"' in start_server
    assert 'LOCAL_LLM_CONFIGURED=false' in start_server
    assert 'GEMINI_LLM_CONFIGURED=false' in start_server
    assert 'GEMINI_API_KEY' in start_server
    assert (
        'run_semantic_probe_set "$BUILD_SRC_DIR/dist/tts_preprocessor" "dist binary"'
        in remote_build
    )
    assert (
        'run_semantic_probe_set \\\n'
        '    "$PREPARED_PACKAGE_DIR/tts-preprocessor" \\\n'
        '    "staging packaged binary"'
        in remote_build
    )
    assert (
        'run_semantic_probe_set "$PACKAGE_DIR/tts-preprocessor" '
        '"published packaged binary"'
        in remote_build
    )
    assert "--runtime binary" in remote_build
    assert '"$BUILD_SRC_DIR"' in remote_build
    assert "rollback_publish" not in remote_build
