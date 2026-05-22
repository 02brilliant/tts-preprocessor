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
SMOKE_TEXT="2천8백28억, 2천8백28억테스트"
SMOKE_EXPECTED="이천팔백이십팔억, 이천팔백이십팔억 테스트"

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

echo "[remote-build] Running source smoke..."
(
  cd "$BUILD_SRC_DIR"
  "$BUILD_ENV_DIR/bin/python" - <<'PY'
import enum

if not hasattr(enum, "StrEnum"):
    class StrEnum(str, enum.Enum):
        def __str__(self):
            return self.value

        @staticmethod
        def _generate_next_value_(name, start, count, last_values):
            return name.lower()

    enum.StrEnum = StrEnum

from engine.main import transform_with_rollout

cases = [
    (
        "2천8백28억, 2천8백28억테스트",
        "이천팔백이십팔억, 이천팔백이십팔억 테스트",
    ),
    (
        "2345억, 2,345억, 1만, 140만, 3백4십만, 5억4천만, 12만3천4백, 2백만3천4백, 54천만, 1억2천3백만4천5백, 25.50억, 2천8백28억테스트, 2천8백28억abc",
        "이천삼백사십오억, 이천삼백사십오억, 일만, 백사십만, 삼백사십만, 오억사천만, 십이만삼천사백, 이백만삼천사백, 오십사천만, 일억이천삼백만사천오백, 이십오쩜오공 억, 이천팔백이십팔억 테스트, 이천팔백이십팔억abc",
    ),
]

for text, expected in cases:
    actual = transform_with_rollout(text, mode="span_default", include_debug=False)
    if actual != expected:
        raise SystemExit(
            "remote source smoke failed\n"
            f"input={text!r}\n"
            f"expected={expected!r}\n"
            f"actual={actual!r}"
        )

print("[OK] remote build source smoke")
PY
)

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

echo "[remote-build] Running dist binary smoke..."
SMOKE_ACTUAL="$("$BUILD_SRC_DIR/dist/tts_preprocessor" --rollout-mode span_default --text "$SMOKE_TEXT")"
if [[ "$SMOKE_ACTUAL" != "$SMOKE_EXPECTED" ]]; then
  echo "[remote-build][ERROR] dist binary smoke failed" >&2
  echo "input: $SMOKE_TEXT" >&2
  echo "expected: $SMOKE_EXPECTED" >&2
  echo "actual: $SMOKE_ACTUAL" >&2
  exit 1
fi
echo "[OK] remote dist binary smoke"

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

echo "[remote-build] Running packaged binary smoke..."
SMOKE_ACTUAL="$("$PACKAGE_DIR/bin/tts_preprocessor" --rollout-mode span_default --text "$SMOKE_TEXT")"
if [[ "$SMOKE_ACTUAL" != "$SMOKE_EXPECTED" ]]; then
  echo "[remote-build][ERROR] packaged binary smoke failed" >&2
  echo "input: $SMOKE_TEXT" >&2
  echo "expected: $SMOKE_EXPECTED" >&2
  echo "actual: $SMOKE_ACTUAL" >&2
  exit 1
fi
echo "[OK] remote packaged binary smoke"

(
  cd "$PACKAGES_DIR"
  zip -qr "$ARCHIVE_PATH" "tts-preprocessor"
)

rm -rf "$BUILD_SRC_DIR"

echo "Remote package built: $ARCHIVE_PATH"
