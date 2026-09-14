#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PYINSTALLER_BIN="$VENV_DIR/bin/pyinstaller"
REQUIRED_PYTHON_SERIES="3.13"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build"
STANDARD_SPEC_FILE="$ROOT_DIR/tts_preprocessor.spec"
SIMPLIFIED_SPEC_FILE="$ROOT_DIR/tts_preprocessor_simplified.spec"
STANDARD_LLM_SPEC_FILE="$ROOT_DIR/tts_preprocessor_standard_llm.spec"
NATURAL_LLM_SPEC_FILE="$ROOT_DIR/tts_preprocessor_natural_llm.spec"
STANDARD_ENTRYPOINT="$ROOT_DIR/bin/build_binary_entrypoint.py"
SIMPLIFIED_ENTRYPOINT="$ROOT_DIR/bin/build_simplified_binary_entrypoint.py"
LLM_CLI_ENTRYPOINT="$ROOT_DIR/bin/integrated_llm_cli.py"
STANDARD_LLM_ENTRYPOINT="$ROOT_DIR/bin/build_standard_llm_entrypoint.py"
NATURAL_LLM_ENTRYPOINT="$ROOT_DIR/bin/build_natural_llm_entrypoint.py"
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

for required_file in "$STANDARD_SPEC_FILE" "$SIMPLIFIED_SPEC_FILE" "$STANDARD_LLM_SPEC_FILE" "$NATURAL_LLM_SPEC_FILE" "$STANDARD_ENTRYPOINT" "$SIMPLIFIED_ENTRYPOINT" "$LLM_CLI_ENTRYPOINT" "$STANDARD_LLM_ENTRYPOINT" "$NATURAL_LLM_ENTRYPOINT"; do
  if [[ ! -f "$required_file" ]]; then
    echo "Missing build file: $required_file" >&2
    exit 1
  fi
done

cd "$ROOT_DIR"
rm -rf "$DIST_DIR" "$BUILD_DIR"

TTS_PREPROCESSOR_EXECUTABLE_NAME="tts-preprocessor-standard" \
  "$PYINSTALLER_BIN" \
    --clean \
    --noconfirm \
    "$STANDARD_SPEC_FILE"
if [[ ! -f "$DIST_DIR/tts-preprocessor-standard" ]]; then
  echo "Binary build failed: $DIST_DIR/tts-preprocessor-standard not found" >&2
  exit 1
fi

echo "[build-binary] Running dist binary smoke..."
SMOKE_ACTUAL="$("$DIST_DIR/tts-preprocessor-standard" --text "$SMOKE_TEXT")"
if [[ "$SMOKE_ACTUAL" != "$SMOKE_EXPECTED" ]]; then
  echo "[build-binary][ERROR] dist binary smoke failed" >&2
  echo "input: $SMOKE_TEXT" >&2
  echo "expected: $SMOKE_EXPECTED" >&2
  echo "actual: $SMOKE_ACTUAL" >&2
  exit 1
fi
echo "[OK] local dist binary smoke"

TTS_PREPROCESSOR_SIMPLIFIED_EXECUTABLE_NAME="tts-preprocessor-simplified" \
  "$PYINSTALLER_BIN" \
    --clean \
    --noconfirm \
    "$SIMPLIFIED_SPEC_FILE"
if [[ ! -f "$DIST_DIR/tts-preprocessor-simplified" ]]; then
  echo "Simplified binary build failed: $DIST_DIR/tts-preprocessor-simplified not found" >&2
  exit 1
fi
SIMPLIFIED_SMOKE_ACTUAL="$("$DIST_DIR/tts-preprocessor-simplified" --text "ABC와 3kg")"
if [[ "$SIMPLIFIED_SMOKE_ACTUAL" != "ABC와 삼-킬로그램" ]]; then
  echo "Simplified dist binary smoke failed" >&2
  echo "expected: ABC와 삼-킬로그램" >&2
  echo "actual: $SIMPLIFIED_SMOKE_ACTUAL" >&2
  exit 1
fi
echo "[OK] local simplified dist binary smoke"

TTS_PREPROCESSOR_STANDARD_LLM_EXECUTABLE_NAME="tts-preprocessor-standard-llm" \
  "$PYINSTALLER_BIN" \
    --clean \
    --noconfirm \
    "$STANDARD_LLM_SPEC_FILE"
if [[ ! -f "$DIST_DIR/tts-preprocessor-standard-llm" || ! -x "$DIST_DIR/tts-preprocessor-standard-llm" ]]; then
  echo "Stage 3 binary build failed" >&2
  exit 1
fi
TTS_PREPROCESSOR_NATURAL_LLM_EXECUTABLE_NAME="tts-preprocessor-natural-llm" \
  "$PYINSTALLER_BIN" \
    --clean \
    --noconfirm \
    "$NATURAL_LLM_SPEC_FILE"
if [[ ! -f "$DIST_DIR/tts-preprocessor-natural-llm" || ! -x "$DIST_DIR/tts-preprocessor-natural-llm" ]]; then
  echo "Stage 4 binary build failed" >&2
  exit 1
fi
"$DIST_DIR/tts-preprocessor-standard-llm" --check >/dev/null
"$DIST_DIR/tts-preprocessor-natural-llm" --check >/dev/null
echo "[OK] Integrated LLM runtime asset checks"

echo "Built stage 1 binary: $DIST_DIR/tts-preprocessor-simplified"
echo "Built stage 2 binary: $DIST_DIR/tts-preprocessor-standard"
echo "Built stage 3 binary: $DIST_DIR/tts-preprocessor-standard-llm"
echo "Built stage 4 binary: $DIST_DIR/tts-preprocessor-natural-llm"
