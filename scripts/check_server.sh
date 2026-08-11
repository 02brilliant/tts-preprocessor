#!/usr/bin/env bash

set -euo pipefail

SERVER_HOST="10.20.10.162"
SERVER_PORT=8010

WEB_URL="http://${SERVER_HOST}:${SERVER_PORT}/web/"
LINUX_DOWNLOAD_URL="http://${SERVER_HOST}:${SERVER_PORT}/downloads/tts-preprocessor-linux.zip"
MACOS_DOWNLOAD_URL="http://${SERVER_HOST}:${SERVER_PORT}/downloads/tts-preprocessor-macos.zip"
WINDOWS_DOWNLOAD_URL="http://${SERVER_HOST}:${SERVER_PORT}/downloads/tts-preprocessor-windows.zip"
DOCS_URL="http://${SERVER_HOST}:${SERVER_PORT}/docs"
TRANSFORM_URL="http://${SERVER_HOST}:${SERVER_PORT}/api/transform"
LLM_MODELS_URL="http://${SERVER_HOST}:${SERVER_PORT}/api/llm/models"
LLM_TRANSFORM_URL="http://${SERVER_HOST}:${SERVER_PORT}/api/llm/transform"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

check_get() {
  local name="$1"
  local url="$2"
  local output_file="$3"

  echo "[check] ${name}: ${url}"
  if ! curl -fsS "$url" -o "$output_file"; then
    echo "[FAIL] ${name} request failed: ${url}" >&2
    exit 1
  fi
}

check_optional_get() {
  local name="$1"
  local url="$2"
  local output_file="$3"

  echo "[check] ${name} (optional): ${url}"
  if curl -fsS "$url" -o "$output_file"; then
    echo "[OK] ${name} responded: ${url}"
  else
    echo "[INFO] ${name} is not currently available; continuing: ${url}"
  fi
}

check_post_transform() {
  local output_file="$1"
  local payload='{"text":"K-1, K-푸드, 112명, 6월"}'
  local expected_normalized='케이-원, 케이푸드, 백십이 명, 유월'

  # Tiny API wiring sanity canary only:
  # this checks the packaged binary path and HTTP wiring are alive.
  # It is not a semantic regression gate; feature validation belongs in
  # scripts/probes/run_semantic_probes.py --suite core --runtime api --api ...
  echo "[check] API transform: ${TRANSFORM_URL}"
  if ! curl -fsS \
    -X POST "$TRANSFORM_URL" \
    -H "Content-Type: application/json" \
    --data "$payload" \
    -o "$output_file"; then
    echo "[FAIL] API transform request failed: ${TRANSFORM_URL}" >&2
    exit 1
  fi

  if ! grep -q '"normalized_text"' "$output_file"; then
    echo "[FAIL] API transform response does not contain normalized_text" >&2
    cat "$output_file" >&2
    exit 1
  fi

  if ! grep -Fq "$expected_normalized" "$output_file"; then
    echo "[FAIL] API transform response does not contain expected canonical output" >&2
    echo "[FAIL] expected: ${expected_normalized}" >&2
    cat "$output_file" >&2
    exit 1
  fi
}

check_llm_models() {
  local output_file="$1"

  echo "[check] LLM model list: ${LLM_MODELS_URL}"
  if ! curl -fsS "$LLM_MODELS_URL" -o "$output_file"; then
    echo "[FAIL] LLM model list request failed: ${LLM_MODELS_URL}" >&2
    exit 1
  fi

  if ! grep -Fq '"default_model":"gemma4:31b"' "$output_file"; then
    echo "[FAIL] LLM model list response does not contain the configured default model" >&2
    exit 1
  fi
}

check_post_llm_transform() {
  local output_file="$1"
  local payload='{"normalized_text":"LLM 배포 확인입니다.","model":"gemma4:31b"}'

  echo "[check] Integrated LLM transform: ${LLM_TRANSFORM_URL}"
  if ! curl -fsS \
    -X POST "$LLM_TRANSFORM_URL" \
    -H "Content-Type: application/json" \
    --data "$payload" \
    -o "$output_file"; then
    echo "[FAIL] LLM transform request failed: ${LLM_TRANSFORM_URL}" >&2
    exit 1
  fi

  if ! grep -q '"speech_text"' "$output_file"; then
    echo "[FAIL] LLM transform response does not contain speech_text" >&2
    exit 1
  fi
}

WEB_OUTPUT="${TMP_DIR}/web.html"
LINUX_DOWNLOAD_OUTPUT="${TMP_DIR}/tts-preprocessor-linux.zip"
MACOS_DOWNLOAD_OUTPUT="${TMP_DIR}/tts-preprocessor-macos.zip"
WINDOWS_DOWNLOAD_OUTPUT="${TMP_DIR}/tts-preprocessor-windows.zip"
DOCS_OUTPUT="${TMP_DIR}/docs.html"
TRANSFORM_OUTPUT="${TMP_DIR}/transform.json"
LLM_MODELS_OUTPUT="${TMP_DIR}/llm-models.json"
LLM_TRANSFORM_OUTPUT="${TMP_DIR}/llm-transform.json"

check_get "Web page" "$WEB_URL" "$WEB_OUTPUT"
check_get "Linux release download" "$LINUX_DOWNLOAD_URL" "$LINUX_DOWNLOAD_OUTPUT"
check_get "macOS release download" "$MACOS_DOWNLOAD_URL" "$MACOS_DOWNLOAD_OUTPUT"
check_optional_get "Windows release download" "$WINDOWS_DOWNLOAD_URL" "$WINDOWS_DOWNLOAD_OUTPUT"
check_get "API docs" "$DOCS_URL" "$DOCS_OUTPUT"
check_post_transform "$TRANSFORM_OUTPUT"
check_llm_models "$LLM_MODELS_OUTPUT"
check_post_llm_transform "$LLM_TRANSFORM_OUTPUT"

echo "[OK] Web page responded: ${WEB_URL}"
echo "[OK] Linux release download responded: ${LINUX_DOWNLOAD_URL}"
echo "[OK] macOS release download responded: ${MACOS_DOWNLOAD_URL}"
echo "[OK] API docs responded: ${DOCS_URL}"
echo "[OK] API transform responded: ${TRANSFORM_URL}"
echo "[OK] LLM model list responded: ${LLM_MODELS_URL}"
echo "[OK] LLM transform responded: ${LLM_TRANSFORM_URL}"
echo "[OK] Server validation completed successfully."
