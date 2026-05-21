#!/usr/bin/env bash

set -euo pipefail

if [[ $# -gt 1 ]]; then
  echo "Usage: bash scripts/build_remote_package.sh [ignored-version]" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/app"
BUILD_SRC_DIR="$ROOT_DIR/buildsrc"
BUILD_ENV_DIR="$ROOT_DIR/buildenv"
LOG_DIR="$ROOT_DIR/logs"
PACKAGES_DIR="$APP_DIR/packages"
DOWNLOADS_DIR="$APP_DIR/downloads"
ARCHIVE_NAME="tts-preprocessor.zip"
PACKAGE_DIR="$PACKAGES_DIR/tts-preprocessor"
ARCHIVE_PATH="$DOWNLOADS_DIR/$ARCHIVE_NAME"
README_TEMPLATE_PATH="$BUILD_SRC_DIR/docs/Release_Package_README.txt"
PYINSTALLER_BIN="$BUILD_ENV_DIR/bin/pyinstaller"
RUNTIME_HOOK_DIR="$BUILD_SRC_DIR/pyinstaller_runtime_hooks"
STR_ENUM_RUNTIME_HOOK="$RUNTIME_HOOK_DIR/enum_strenum_compat.py"
PROBE_SOURCE_DIR="$BUILD_SRC_DIR/scripts/probes"
SEMANTIC_PROBE_RUNNER="$PROBE_SOURCE_DIR/run_semantic_probes.py"

run_semantic_probe_set() {
  local binary_path="$1"
  local label="$2"

  if [[ ! -f "$binary_path" ]]; then
    echo "[remote-build][ERROR] Missing $label binary: $binary_path" >&2
    exit 1
  fi

  if [[ ! -f "$SEMANTIC_PROBE_RUNNER" ]]; then
    echo "[remote-build][ERROR] Missing semantic probe runner: $SEMANTIC_PROBE_RUNNER" >&2
    exit 1
  fi

  echo "[remote-build] Running $label semantic probes..."
  "$BUILD_ENV_DIR/bin/python" \
    "$SEMANTIC_PROBE_RUNNER" \
    --runtime binary \
    --binary "$binary_path"
  echo "[OK] remote $label semantic probes"
}

mkdir -p "$LOG_DIR" "$PACKAGES_DIR" "$DOWNLOADS_DIR"

if [[ ! -d "$BUILD_SRC_DIR/engine" || ! -f "$BUILD_SRC_DIR/bin/build_binary_entrypoint.py" ]]; then
  echo "Missing remote build sources under $BUILD_SRC_DIR" >&2
  exit 1
fi

if [[ ! -d "$BUILD_ENV_DIR" ]]; then
  python3 -m venv "$BUILD_ENV_DIR"
fi

"$BUILD_ENV_DIR/bin/pip" install --quiet --upgrade pip pyinstaller

rm -rf "$BUILD_SRC_DIR/dist" "$BUILD_SRC_DIR/build" "$BUILD_SRC_DIR/tts_preprocessor.spec"
mkdir -p "$RUNTIME_HOOK_DIR"
cat > "$STR_ENUM_RUNTIME_HOOK" <<'PY'
import enum

if not hasattr(enum, "StrEnum"):
    class StrEnum(str, enum.Enum):
        def __str__(self):
            return self.value

        @staticmethod
        def _generate_next_value_(name, start, count, last_values):
            return name.lower()

    enum.StrEnum = StrEnum
PY

(
  cd "$BUILD_SRC_DIR"
  "$PYINSTALLER_BIN" \
    --clean \
    --onefile \
    --name tts_preprocessor \
    --paths "$BUILD_SRC_DIR" \
    --collect-submodules engine \
    --add-data "$BUILD_SRC_DIR/engine/data:engine/data" \
    --runtime-hook "$STR_ENUM_RUNTIME_HOOK" \
    bin/build_binary_entrypoint.py
)

if [[ ! -f "$BUILD_SRC_DIR/dist/tts_preprocessor" ]]; then
  echo "Remote binary build failed." >&2
  exit 1
fi

run_semantic_probe_set "$BUILD_SRC_DIR/dist/tts_preprocessor" "dist binary"

find "$PACKAGES_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
find "$DOWNLOADS_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

mkdir -p "$PACKAGE_DIR/bin"

if [[ -f "$README_TEMPLATE_PATH" ]]; then
  cp "$README_TEMPLATE_PATH" "$PACKAGE_DIR/README.txt"
else
  printf 'tts-preprocessor\n' > "$PACKAGE_DIR/README.txt"
fi

cp "$BUILD_SRC_DIR/dist/tts_preprocessor" "$PACKAGE_DIR/bin/tts_preprocessor"
chmod +x "$PACKAGE_DIR/bin/tts_preprocessor"

run_semantic_probe_set "$PACKAGE_DIR/bin/tts_preprocessor" "packaged binary"

(
  cd "$PACKAGES_DIR"
  zip -qr "$ARCHIVE_PATH" "tts-preprocessor"
)

rm -rf "$BUILD_SRC_DIR"

echo "Remote package built: $ARCHIVE_PATH"
