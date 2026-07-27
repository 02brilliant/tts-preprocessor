#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: bash scripts/build_remote_package.sh {prepare|publish|cleanup} <deploy-id>" >&2
  exit 2
fi

ACTION="$1"
DEPLOY_ID="$2"
case "$ACTION" in
  prepare|publish|cleanup) ;;
  *)
    echo "Unknown action: $ACTION" >&2
    exit 2
    ;;
esac
if [[ ! "$DEPLOY_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "[remote-build][ERROR] Invalid deploy ID: $DEPLOY_ID" >&2
  exit 2
fi

ROOT_DIR="$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)"
APP_DIR="$ROOT_DIR/app"
BUILD_SRC_DIR="$ROOT_DIR/buildsrc"
BUILD_ENV_DIR="$ROOT_DIR/buildenv"
REQUIRED_PYTHON_SERIES="3.13"
PACKAGES_DIR="$APP_DIR/packages"
DOWNLOADS_DIR="$APP_DIR/downloads"
PACKAGE_DIR="$PACKAGES_DIR/tts-preprocessor"
ARCHIVE_NAME="tts-preprocessor-linux.zip"
ARCHIVE_PATH="$DOWNLOADS_DIR/$ARCHIVE_NAME"
README_TEMPLATE_PATH="$BUILD_SRC_DIR/docs/Release_Package_README.txt"
PYINSTALLER_BIN="$BUILD_ENV_DIR/bin/pyinstaller"
SEMANTIC_PROBE_RUNNER="$BUILD_SRC_DIR/scripts/probes/run_semantic_probes.py"
SERVER_PID_FILE="$ROOT_DIR/run/tts_web_service.pid"

PREPARE_PARENT="$PACKAGES_DIR/.tts-preprocessor.prepare.$DEPLOY_ID"
PREPARED_PACKAGE_DIR="$PREPARE_PARENT/tts-preprocessor"
PREPARED_MARKER="$PREPARE_PARENT/prepare.marker"
PUBLISHED_MARKER="$PREPARE_PARENT/published.marker"
PREPARED_ARCHIVE="$DOWNLOADS_DIR/.tts-preprocessor-linux.prepare.$DEPLOY_ID.zip"
PREPARE_SUCCEEDED=false
PUBLISH_SUCCEEDED=false

run_semantic_probe_set() {
  local binary_path="$1"
  local label="$2"

  if [[ ! -f "$binary_path" || ! -x "$binary_path" ]]; then
    echo "[remote-build][ERROR] Missing executable $label binary: $binary_path" >&2
    return 1
  fi
  if [[ ! -f "$SEMANTIC_PROBE_RUNNER" ]]; then
    echo "[remote-build][ERROR] Missing semantic probe runner: $SEMANTIC_PROBE_RUNNER" >&2
    return 1
  fi

  echo "[remote-build] Running $label semantic probes..."
  if ! "$BUILD_ENV_DIR/bin/python" \
    "$SEMANTIC_PROBE_RUNNER" \
    --suite core \
    --runtime binary \
    --binary "$binary_path"; then
    echo "[remote-build][ERROR] $label semantic probes failed." >&2
    return 1
  fi
  echo "[remote-build][OK] $label semantic probes passed."
}

validate_build_environment() {
  local required_executable
  local required_command
  local python_runtime

  if [[ ! -d "$BUILD_ENV_DIR" ]]; then
    echo "[remote-build][ERROR] Missing existing build environment: $BUILD_ENV_DIR" >&2
    echo "[remote-build][ERROR] Prepare the approved Ubuntu 22.04 buildenv; this script will not create it." >&2
    return 1
  fi

  for required_executable in \
    "$BUILD_ENV_DIR/bin/python" \
    "$BUILD_ENV_DIR/bin/pip" \
    "$BUILD_ENV_DIR/bin/pyinstaller"; do
    if [[ ! -x "$required_executable" ]]; then
      echo "[remote-build][ERROR] Missing buildenv executable: $required_executable" >&2
      echo "[remote-build][ERROR] Repair the existing buildenv; this script will not install or upgrade it." >&2
      return 1
    fi
  done

  for required_command in \
    bash python3 mkdir rm mv cp chmod find sort stat sha256sum unzip; do
    if ! command -v "$required_command" >/dev/null 2>&1; then
      echo "[remote-build][ERROR] Missing required remote command: $required_command" >&2
      return 1
    fi
  done

  python_runtime="$("$BUILD_ENV_DIR/bin/python" -c 'import sys, sysconfig; print("%d.%d:%d" % (sys.version_info.major, sys.version_info.minor, int(bool(sysconfig.get_config_var("Py_GIL_DISABLED")))))')"
  if [[ "$python_runtime" != "$REQUIRED_PYTHON_SERIES:0" ]]; then
    echo "[remote-build][ERROR] buildenv must use standard-GIL Python $REQUIRED_PYTHON_SERIES.x; got: $python_runtime" >&2
    return 1
  fi
}

validate_build_sources() {
  local required_source

  for required_source in \
    "$BUILD_SRC_DIR/engine" \
    "$BUILD_SRC_DIR/bin/build_binary_entrypoint.py" \
    "$BUILD_SRC_DIR/tts_preprocessor.spec" \
    "$README_TEMPLATE_PATH" \
    "$SEMANTIC_PROBE_RUNNER"; do
    if [[ ! -e "$required_source" ]]; then
      echo "[remote-build][ERROR] Missing remote build source: $required_source" >&2
      return 1
    fi
  done
}

validate_linux_archive() {
  local archive_path="$1"
  local contents
  local expected

  unzip -tq "$archive_path"
  contents="$(unzip -Z1 "$archive_path" | LC_ALL=C sort)"
  expected=$'tts-preprocessor/README.txt\ntts-preprocessor/tts-preprocessor'
  if [[ "$contents" != "$expected" ]]; then
    echo "[remote-build][ERROR] Unexpected Linux ZIP contents:" >&2
    printf '%s\n' "$contents" >&2
    return 1
  fi
}

calculate_sha256() {
  local path="$1"
  local digest

  digest="$(sha256sum "$path")"
  digest="${digest%% *}"
  if [[ ! "$digest" =~ ^[0-9a-f]{64}$ ]]; then
    echo "[remote-build][ERROR] Could not calculate SHA-256 for: $path" >&2
    return 1
  fi
  printf '%s\n' "$digest"
}

write_prepare_marker() {
  local archive_digest="$1"

  {
    printf 'deploy_id=%s\n' "$DEPLOY_ID"
    printf 'package_path=%s\n' "$PREPARED_PACKAGE_DIR"
    printf 'archive_path=%s\n' "$PREPARED_ARCHIVE"
    printf 'archive_sha256=%s\n' "$archive_digest"
  } > "$PREPARED_MARKER"
}

validate_prepare_marker() {
  local -a marker_lines=()
  local marker_line
  local archive_digest

  if [[ ! -f "$PREPARED_MARKER" ]]; then
    echo "[remote-build][ERROR] Missing prepare marker for deploy ID: $DEPLOY_ID" >&2
    return 1
  fi
  while IFS= read -r marker_line; do
    marker_lines[${#marker_lines[@]}]="$marker_line"
  done < "$PREPARED_MARKER"
  if [[ "${#marker_lines[@]}" -ne 4 \
    || "${marker_lines[0]}" != "deploy_id=$DEPLOY_ID" \
    || "${marker_lines[1]}" != "package_path=$PREPARED_PACKAGE_DIR" \
    || "${marker_lines[2]}" != "archive_path=$PREPARED_ARCHIVE" \
    || ! "${marker_lines[3]}" =~ ^archive_sha256=([0-9a-f]{64})$ ]]; then
    echo "[remote-build][ERROR] Invalid or stale prepare marker for deploy ID: $DEPLOY_ID" >&2
    return 1
  fi
  if [[ ! -d "$PREPARED_PACKAGE_DIR" \
    || ! -x "$PREPARED_PACKAGE_DIR/tts-preprocessor" \
    || ! -f "$PREPARED_ARCHIVE" ]]; then
    echo "[remote-build][ERROR] Prepared Linux artifacts are incomplete for deploy ID: $DEPLOY_ID" >&2
    return 1
  fi

  archive_digest="$(calculate_sha256 "$PREPARED_ARCHIVE")"
  if [[ "$archive_digest" != "${BASH_REMATCH[1]}" ]]; then
    echo "[remote-build][ERROR] Prepared Linux ZIP SHA-256 does not match its marker." >&2
    return 1
  fi
  validate_linux_archive "$PREPARED_ARCHIVE"
}

cleanup_failed_prepare() {
  local original_status=$?

  trap - EXIT
  if [[ "$ACTION" == "prepare" && "$PREPARE_SUCCEEDED" != true ]]; then
    rm -rf -- "$PREPARE_PARENT" "$BUILD_SRC_DIR/build" "$BUILD_SRC_DIR/dist"
    rm -f -- "$PREPARED_ARCHIVE"
    echo "[remote-build][ERROR] Linux prepare failed; staging was removed and production artifacts were unchanged." >&2
  fi
  return "$original_status"
}

report_publish_failure() {
  local original_status=$?

  trap - EXIT
  if [[ "$ACTION" == "publish" && "$PUBLISH_SUCCEEDED" != true ]]; then
    echo "[remote-build][ERROR] Linux publish failed after the server was stopped." >&2
    echo "[remote-build][ERROR] The server was not restarted." >&2
    echo "[remote-build][ERROR] The operational package or Linux ZIP may be partially updated." >&2
    printf '[remote-build][ERROR] Current package executable: %s\n' \
      "$([[ -x "$PACKAGE_DIR/tts-preprocessor" ]] && printf present || printf missing)" >&2
    printf '[remote-build][ERROR] Current Linux ZIP: %s\n' \
      "$([[ -f "$ARCHIVE_PATH" ]] && printf present || printf missing)" >&2
    echo "[remote-build][ERROR] Fix the reported issue and run the full deployment again." >&2
  fi
  return "$original_status"
}

create_prepared_archive() {
  "$BUILD_ENV_DIR/bin/python" - "$PREPARE_PARENT" "$PREPARED_ARCHIVE" <<'PY'
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

prepare_parent = Path(sys.argv[1])
archive_path = Path(sys.argv[2])
package_dir = prepare_parent / "tts-preprocessor"
with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
    archive.write(
        package_dir / "README.txt",
        "tts-preprocessor/README.txt",
    )
    archive.write(
        package_dir / "tts-preprocessor",
        "tts-preprocessor/tts-preprocessor",
    )
PY
}

prepare_linux_release() {
  local archive_digest

  trap cleanup_failed_prepare EXIT
  validate_build_environment
  validate_build_sources
  mkdir -p "$PACKAGES_DIR" "$DOWNLOADS_DIR"

  rm -rf -- "$BUILD_SRC_DIR/dist" "$BUILD_SRC_DIR/build" "$PREPARE_PARENT"
  rm -f -- "$PREPARED_ARCHIVE"

  echo "[remote-build] Deploy ID: $DEPLOY_ID"
  echo "[remote-build] PyInstaller version: $("$PYINSTALLER_BIN" --version)"
  echo "[remote-build] Preparing Linux binary without changing production artifacts..."
  (
    cd "$BUILD_SRC_DIR"
    "$PYINSTALLER_BIN" \
      --clean \
      --noconfirm \
      "$BUILD_SRC_DIR/tts_preprocessor.spec"
  )

  run_semantic_probe_set "$BUILD_SRC_DIR/dist/tts_preprocessor" "dist binary"

  mkdir -p "$PREPARED_PACKAGE_DIR"
  cp "$README_TEMPLATE_PATH" "$PREPARED_PACKAGE_DIR/README.txt"
  cp "$BUILD_SRC_DIR/dist/tts_preprocessor" "$PREPARED_PACKAGE_DIR/tts-preprocessor"
  chmod +x "$PREPARED_PACKAGE_DIR/tts-preprocessor"
  run_semantic_probe_set \
    "$PREPARED_PACKAGE_DIR/tts-preprocessor" \
    "staging packaged binary"

  create_prepared_archive
  validate_linux_archive "$PREPARED_ARCHIVE"
  archive_digest="$(calculate_sha256 "$PREPARED_ARCHIVE")"
  write_prepare_marker "$archive_digest"
  validate_prepare_marker

  PREPARE_SUCCEEDED=true
  trap - EXIT
  echo "[remote-build][OK] Linux release prepared and verified for deploy ID: $DEPLOY_ID"
  echo "[remote-build][OK] Production package and downloads were not changed."
}

verify_server_stopped() {
  local server_pid=""

  if [[ -f "$SERVER_PID_FILE" ]]; then
    IFS= read -r server_pid < "$SERVER_PID_FILE" || true
    if [[ "$server_pid" =~ ^[0-9]+$ ]] && kill -0 "$server_pid" 2>/dev/null; then
      echo "[remote-build][ERROR] Server PID $server_pid is still running; refusing Linux publish." >&2
      return 1
    fi
  fi
}

publish_linux_release() {
  trap report_publish_failure EXIT
  validate_build_environment
  validate_build_sources
  validate_prepare_marker
  verify_server_stopped

  if [[ ! -d "$PACKAGES_DIR" || ! -d "$DOWNLOADS_DIR" ]]; then
    echo "[remote-build][ERROR] Production package/download parent directory is missing." >&2
    return 1
  fi
  if [[ -e "$PACKAGE_DIR" && ! -d "$PACKAGE_DIR" ]]; then
    echo "[remote-build][ERROR] Production package path is not a directory: $PACKAGE_DIR" >&2
    return 1
  fi

  echo "[remote-build] Publishing verified Linux artifacts for deploy ID: $DEPLOY_ID"
  rm -rf -- "$PACKAGE_DIR"
  mv -- "$PREPARED_PACKAGE_DIR" "$PACKAGE_DIR"
  rm -f -- "$ARCHIVE_PATH"
  mv -- "$PREPARED_ARCHIVE" "$ARCHIVE_PATH"

  run_semantic_probe_set "$PACKAGE_DIR/tts-preprocessor" "published packaged binary"
  printf 'deploy_id=%s\n' "$DEPLOY_ID" > "$PUBLISHED_MARKER"
  PUBLISH_SUCCEEDED=true
  trap - EXIT
  echo "[remote-build][OK] Linux package published: $ARCHIVE_PATH"
}

cleanup_remote_build_sources() {
  rm -rf -- \
    "$PREPARE_PARENT" \
    "$BUILD_SRC_DIR/build" \
    "$BUILD_SRC_DIR/dist" \
    "$BUILD_SRC_DIR"
  rm -f -- "$PREPARED_ARCHIVE"
  echo "[remote-build][OK] Temporary Linux build sources removed for deploy ID: $DEPLOY_ID"
}

case "$ACTION" in
  prepare) prepare_linux_release ;;
  publish) publish_linux_release ;;
  cleanup) cleanup_remote_build_sources ;;
esac
