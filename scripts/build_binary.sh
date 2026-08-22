#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PYINSTALLER_BIN="$VENV_DIR/bin/pyinstaller"
REQUIRED_PYTHON_SERIES="3.13"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build"
STAGE1_SPEC_FILE="$ROOT_DIR/tts_preprocessor.spec"
SIMPLIFIED_SPEC_FILE="$ROOT_DIR/tts_preprocessor_simplified.spec"
LLM_MINIMAL_SPEC_FILE="$ROOT_DIR/tts_preprocessor_llm_minimal.spec"
LLM_NATURAL_SPEC_FILE="$ROOT_DIR/tts_preprocessor_llm_natural.spec"
STAGE1_ENTRYPOINT="$ROOT_DIR/bin/build_binary_entrypoint.py"
SIMPLIFIED_ENTRYPOINT="$ROOT_DIR/bin/build_simplified_binary_entrypoint.py"
LLM_CLI_ENTRYPOINT="$ROOT_DIR/bin/integrated_llm_cli.py"
LLM_MINIMAL_ENTRYPOINT="$ROOT_DIR/bin/build_llm_minimal_entrypoint.py"
LLM_NATURAL_ENTRYPOINT="$ROOT_DIR/bin/build_llm_natural_entrypoint.py"
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

for required_file in "$STAGE1_SPEC_FILE" "$SIMPLIFIED_SPEC_FILE" "$LLM_MINIMAL_SPEC_FILE" "$LLM_NATURAL_SPEC_FILE" "$STAGE1_ENTRYPOINT" "$SIMPLIFIED_ENTRYPOINT" "$LLM_CLI_ENTRYPOINT" "$LLM_MINIMAL_ENTRYPOINT" "$LLM_NATURAL_ENTRYPOINT"; do
  if [[ ! -f "$required_file" ]]; then
    echo "Missing build file: $required_file" >&2
    exit 1
  fi
done

cd "$ROOT_DIR"
rm -rf "$DIST_DIR" "$BUILD_DIR"

"$PYINSTALLER_BIN" \
  --clean \
  --noconfirm \
  "$STAGE1_SPEC_FILE"
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

TTS_PREPROCESSOR_SIMPLIFIED_EXECUTABLE_NAME="tts-preprocessor-simplified" \
  "$PYINSTALLER_BIN" \
    --clean \
    --noconfirm \
    "$SIMPLIFIED_SPEC_FILE"
if [[ ! -f "$DIST_DIR/tts-preprocessor-simplified" ]]; then
  echo "Simplified binary build failed: $DIST_DIR/tts-preprocessor-simplified not found" >&2
  exit 1
fi
if [[ "$("$DIST_DIR/tts-preprocessor-simplified" --text "ABC와 3kg")" != "ABC와 삼 킬로그램" ]]; then
  echo "Simplified dist binary smoke failed" >&2
  exit 1
fi
echo "[OK] local simplified dist binary smoke"

TTS_PREPROCESSOR_LLM_MINIMAL_EXECUTABLE_NAME="tts-preprocessor-llm-minimal" \
  "$PYINSTALLER_BIN" \
    --clean \
    --noconfirm \
    "$LLM_MINIMAL_SPEC_FILE"
if [[ ! -f "$DIST_DIR/tts-preprocessor-llm-minimal" || ! -x "$DIST_DIR/tts-preprocessor-llm-minimal" ]]; then
  echo "Level 3 binary build failed" >&2
  exit 1
fi
TTS_PREPROCESSOR_LLM_NATURAL_EXECUTABLE_NAME="tts-preprocessor-llm-natural" \
  "$PYINSTALLER_BIN" \
    --clean \
    --noconfirm \
    "$LLM_NATURAL_SPEC_FILE"
if [[ ! -f "$DIST_DIR/tts-preprocessor-llm-natural" || ! -x "$DIST_DIR/tts-preprocessor-llm-natural" ]]; then
  echo "Level 4 binary build failed" >&2
  exit 1
fi
"$DIST_DIR/tts-preprocessor-llm-minimal" --check >/dev/null
"$DIST_DIR/tts-preprocessor-llm-natural" --check >/dev/null
echo "[OK] Integrated LLM runtime asset checks"

echo "Built stage 1 binary: $DIST_DIR/tts_preprocessor"
echo "Built simplified binary: $DIST_DIR/tts-preprocessor-simplified"
echo "Built level 3 binary: $DIST_DIR/tts-preprocessor-llm-minimal"
echo "Built level 4 binary: $DIST_DIR/tts-preprocessor-llm-natural"
