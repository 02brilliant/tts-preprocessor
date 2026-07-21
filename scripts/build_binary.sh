#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build"
SPEC_FILE="$ROOT_DIR/tts_preprocessor.spec"
SOURCE_ENTRYPOINT="$ROOT_DIR/bin/build_binary_entrypoint.py"
SMOKE_TEXT="2천8백28억, 2천8백28억테스트"
SMOKE_EXPECTED="이천팔백이십팔억, 이천팔백이십팔억 테스트"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Missing virtual environment: $VENV_DIR" >&2
  exit 1
fi

if [[ ! -f "$SOURCE_ENTRYPOINT" ]]; then
  echo "Missing build entrypoint: $SOURCE_ENTRYPOINT" >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"

cd "$ROOT_DIR"
rm -rf "$DIST_DIR" "$BUILD_DIR"

pyinstaller \
  --clean \
  --noconfirm \
  "$SPEC_FILE"
if [[ ! -f "$DIST_DIR/tts_preprocessor" ]]; then
  echo "Binary build failed: $DIST_DIR/tts_preprocessor not found" >&2
  exit 1
fi

echo "[build-binary] Running dist binary smoke..."
SMOKE_ACTUAL="$("$DIST_DIR/tts_preprocessor" --text "$SMOKE_TEXT")"
if [[ "$SMOKE_ACTUAL" != "$SMOKE_EXPECTED" ]]; then
  echo "[build-binary][ERROR] dist binary smoke failed" >&2
  echo "input: $SMOKE_TEXT" >&2
  echo "expected: $SMOKE_EXPECTED" >&2
  echo "actual: $SMOKE_ACTUAL" >&2
  exit 1
fi
echo "[OK] local dist binary smoke"

echo "Built binary: $DIST_DIR/tts_preprocessor"
