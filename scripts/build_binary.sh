#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PYINSTALLER_BIN="$VENV_DIR/bin/pyinstaller"
REQUIRED_PYTHON_SERIES="3.13"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build"
SPEC_FILE="$ROOT_DIR/tts_preprocessor.spec"
SOURCE_ENTRYPOINT="$ROOT_DIR/bin/build_binary_entrypoint.py"
SMOKE_TEXT="2천8백28억, 2천8백28억테스트"
SMOKE_EXPECTED="이천팔백이십팔억, 이천팔백이십팔억 테스트"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "scripts/build_binary.sh is for Linux local validation only." >&2
  echo "Use scripts/build_macos_package.sh for macOS packages." >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Missing virtual environment: $VENV_DIR" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" || ! -x "$PYINSTALLER_BIN" ]]; then
  echo "Missing project Python or PyInstaller executable under: $VENV_DIR/bin" >&2
  exit 1
fi

PYTHON_RUNTIME="$("$PYTHON_BIN" -c 'import sys, sysconfig; print("%d.%d:%d" % (sys.version_info.major, sys.version_info.minor, int(bool(sysconfig.get_config_var("Py_GIL_DISABLED")))))')"
if [[ "$PYTHON_RUNTIME" != "$REQUIRED_PYTHON_SERIES:0" ]]; then
  echo "Project Python must be standard-GIL Python $REQUIRED_PYTHON_SERIES.x; got: $PYTHON_RUNTIME" >&2
  exit 1
fi

if [[ ! -f "$SOURCE_ENTRYPOINT" ]]; then
  echo "Missing build entrypoint: $SOURCE_ENTRYPOINT" >&2
  exit 1
fi

cd "$ROOT_DIR"
rm -rf "$DIST_DIR" "$BUILD_DIR"

"$PYINSTALLER_BIN" \
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
