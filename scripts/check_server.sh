#!/usr/bin/env bash

set -euo pipefail

SERVER_HOST="10.20.10.162"
SERVER_PORT=8010

WEB_URL="http://${SERVER_HOST}:${SERVER_PORT}/web/"
DOWNLOAD_URL="http://${SERVER_HOST}:${SERVER_PORT}/downloads/tts-preprocessor.zip"
DOCS_URL="http://${SERVER_HOST}:${SERVER_PORT}/docs"
TRANSFORM_URL="http://${SERVER_HOST}:${SERVER_PORT}/api/transform"

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

check_post_transform() {
  local output_file="$1"
  local payload='{"text":"K-1, K-푸드, 112명, 6월"}'
  local expected_normalized='케이 원, 케이푸드, 백십이 명, 유월'

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

WEB_OUTPUT="${TMP_DIR}/web.html"
DOWNLOAD_OUTPUT="${TMP_DIR}/tts-preprocessor.zip"
DOCS_OUTPUT="${TMP_DIR}/docs.html"
TRANSFORM_OUTPUT="${TMP_DIR}/transform.json"

check_get "Web page" "$WEB_URL" "$WEB_OUTPUT"
check_get "release download" "$DOWNLOAD_URL" "$DOWNLOAD_OUTPUT"
check_get "API docs" "$DOCS_URL" "$DOCS_OUTPUT"
check_post_transform "$TRANSFORM_OUTPUT"

echo "[OK] Web page responded: ${WEB_URL}"
echo "[OK] release download responded: ${DOWNLOAD_URL}"
echo "[OK] API docs responded: ${DOCS_URL}"
echo "[OK] API transform responded: ${TRANSFORM_URL}"
echo "[OK] Server validation completed successfully."
