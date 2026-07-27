#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PYINSTALLER_BIN="$VENV_DIR/bin/pyinstaller"
REQUIRED_PYTHON_SERIES="3.13"
SPEC_FILE="$ROOT_DIR/tts_preprocessor.spec"
SOURCE_ENTRYPOINT="$ROOT_DIR/bin/build_binary_entrypoint.py"
README_TEMPLATE="$ROOT_DIR/docs/Release_Package_README.txt"
MACOS_BUILD_DIR="$ROOT_DIR/build/macos"
MACOS_DIST_DIR="$MACOS_BUILD_DIR/dist"
MACOS_WORK_DIR="$MACOS_BUILD_DIR/work"
MACOS_BINARY="$MACOS_DIST_DIR/tts-preprocessor"
DOWNLOADS_DIR="$ROOT_DIR/downloads"
ARCHIVE_NAME="tts-preprocessor-macos.zip"
ARCHIVE_PATH="$DOWNLOADS_DIR/$ARCHIVE_NAME"
SMOKE_TEXT="2천8백28억, 2천8백28억테스트"
SMOKE_EXPECTED="이천팔백이십팔억, 이천팔백이십팔억 테스트"

OS_NAME="$(uname -s)"
MACHINE_ARCH="$(uname -m)"
echo "[macos-build] OS: $OS_NAME"
echo "[macos-build] Machine architecture: $MACHINE_ARCH"

if [[ "$OS_NAME" != "Darwin" ]]; then
  echo "[macos-build][ERROR] macOS package builds require Darwin; got: $OS_NAME" >&2
  exit 1
fi

if [[ "$MACHINE_ARCH" != "arm64" ]]; then
  echo "[macos-build][ERROR] This build contract supports Apple Silicon arm64 only; got: $MACHINE_ARCH" >&2
  exit 1
fi

for required_file in \
  "$PYTHON_BIN" \
  "$PYINSTALLER_BIN" \
  "$SPEC_FILE" \
  "$SOURCE_ENTRYPOINT" \
  "$README_TEMPLATE"; do
  if [[ ! -e "$required_file" ]]; then
    echo "[macos-build][ERROR] Missing required file: $required_file" >&2
    exit 1
  fi
done

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[macos-build][ERROR] Project Python is not executable: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -x "$PYINSTALLER_BIN" ]]; then
  echo "[macos-build][ERROR] Project PyInstaller is not executable: $PYINSTALLER_BIN" >&2
  exit 1
fi

PYTHON_ARCH="$("$PYTHON_BIN" -c 'import platform; print(platform.machine())')"
PYTHON_EXECUTABLE="$("$PYTHON_BIN" -c 'import sys; print(sys.executable)')"
PYTHON_RUNTIME="$("$PYTHON_BIN" -c 'import sys, sysconfig; print("%d.%d:%d" % (sys.version_info.major, sys.version_info.minor, int(bool(sysconfig.get_config_var("Py_GIL_DISABLED")))))')"
echo "[macos-build] Python: $PYTHON_EXECUTABLE"
echo "[macos-build] Python architecture: $PYTHON_ARCH"
echo "[macos-build] PyInstaller: $("$PYINSTALLER_BIN" --version)"

if [[ "$PYTHON_RUNTIME" != "$REQUIRED_PYTHON_SERIES:0" ]]; then
  echo "[macos-build][ERROR] Project Python must be standard-GIL Python $REQUIRED_PYTHON_SERIES.x; got: $PYTHON_RUNTIME" >&2
  exit 1
fi

if [[ "$PYTHON_ARCH" != "arm64" ]]; then
  echo "[macos-build][ERROR] Project Python must be arm64; got: $PYTHON_ARCH" >&2
  exit 1
fi

rm -rf -- "$MACOS_BUILD_DIR"
mkdir -p "$MACOS_DIST_DIR" "$MACOS_WORK_DIR" "$DOWNLOADS_DIR"

(
  cd "$ROOT_DIR"
  PYINSTALLER_CONFIG_DIR="$MACOS_BUILD_DIR/pyinstaller-config" \
    TTS_PREPROCESSOR_EXECUTABLE_NAME="tts-preprocessor" \
    "$PYINSTALLER_BIN" \
      --clean \
      --noconfirm \
      --distpath "$MACOS_DIST_DIR" \
      --workpath "$MACOS_WORK_DIR" \
      "$SPEC_FILE"
)

if [[ ! -f "$MACOS_BINARY" ]]; then
  echo "[macos-build][ERROR] Missing built executable: $MACOS_BINARY" >&2
  exit 1
fi

if [[ ! -x "$MACOS_BINARY" ]]; then
  echo "[macos-build][ERROR] Built executable is not executable: $MACOS_BINARY" >&2
  exit 1
fi

FILE_OUTPUT="$(file "$MACOS_BINARY")"
echo "[macos-build] file: $FILE_OUTPUT"
if [[ "$FILE_OUTPUT" != *"Mach-O"* || "$FILE_OUTPUT" != *"arm64"* ]]; then
  echo "[macos-build][ERROR] Expected a Mach-O arm64 executable." >&2
  exit 1
fi

SMOKE_ACTUAL="$("$MACOS_BINARY" --text "$SMOKE_TEXT")"
if [[ "$SMOKE_ACTUAL" != "$SMOKE_EXPECTED" ]]; then
  echo "[macos-build][ERROR] Built executable smoke test failed." >&2
  echo "expected: $SMOKE_EXPECTED" >&2
  echo "actual: $SMOKE_ACTUAL" >&2
  exit 1
fi

STAGING_DIR="$(mktemp -d "$DOWNLOADS_DIR/.tts-preprocessor-macos.XXXXXX")"
trap 'rm -rf -- "$STAGING_DIR"' EXIT
PACKAGE_DIR="$STAGING_DIR/package"
EXTRACT_DIR="$STAGING_DIR/extracted"
TEMP_ARCHIVE="$STAGING_DIR/$ARCHIVE_NAME"
mkdir -p "$PACKAGE_DIR" "$EXTRACT_DIR"

cp "$MACOS_BINARY" "$PACKAGE_DIR/tts-preprocessor"
cp "$README_TEMPLATE" "$PACKAGE_DIR/README.txt"
chmod +x "$PACKAGE_DIR/tts-preprocessor"

(
  cd "$PACKAGE_DIR"
  zip -q "$TEMP_ARCHIVE" "tts-preprocessor" "README.txt"
)

unzip -tq "$TEMP_ARCHIVE"
ARCHIVE_CONTENTS="$(unzip -Z1 "$TEMP_ARCHIVE" | LC_ALL=C sort)"
EXPECTED_CONTENTS=$'README.txt\ntts-preprocessor'
if [[ "$ARCHIVE_CONTENTS" != "$EXPECTED_CONTENTS" ]]; then
  echo "[macos-build][ERROR] Unexpected macOS ZIP contents:" >&2
  printf '%s\n' "$ARCHIVE_CONTENTS" >&2
  exit 1
fi

if printf '%s\n' "$ARCHIVE_CONTENTS" | grep -Eq '(^|/)(engine|tests|docs|\.venv|__pycache__|build)(/|$)|\.py$|\.pyc$'; then
  echo "[macos-build][ERROR] macOS ZIP contains source or development files." >&2
  exit 1
fi

unzip -q "$TEMP_ARCHIVE" -d "$EXTRACT_DIR"
if find "$EXTRACT_DIR" -type l -print -quit | grep -q .; then
  echo "[macos-build][ERROR] Symbolic links are not allowed in the macOS ZIP." >&2
  exit 1
fi
if [[ ! -x "$EXTRACT_DIR/tts-preprocessor" ]]; then
  echo "[macos-build][ERROR] Extracted executable is not executable." >&2
  exit 1
fi

EXTRACTED_SMOKE_ACTUAL="$("$EXTRACT_DIR/tts-preprocessor" --text "$SMOKE_TEXT")"
if [[ "$EXTRACTED_SMOKE_ACTUAL" != "$SMOKE_EXPECTED" ]]; then
  echo "[macos-build][ERROR] Extracted executable smoke test failed." >&2
  exit 1
fi

mv -f -- "$TEMP_ARCHIVE" "$ARCHIVE_PATH"
echo "[macos-build][OK] Executable: $MACOS_BINARY"
echo "[macos-build][OK] Package: $ARCHIVE_PATH"
