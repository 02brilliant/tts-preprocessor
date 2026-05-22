#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_ARCHIVE_PATH="$ROOT_DIR/downloads/tts-preprocessor.zip"

REMOTE_USER="brilliant"
REMOTE_HOST="10.20.10.162"
REMOTE_BASE_DIR="~/tts-preprocessor"

REMOTE_APP_DIR="$REMOTE_BASE_DIR/app"
REMOTE_PACKAGES_DIR="$REMOTE_APP_DIR/packages"
REMOTE_DOWNLOADS_DIR="$REMOTE_APP_DIR/downloads"

REMOTE_BUILD_SRC_DIR="$REMOTE_BASE_DIR/buildsrc"
REMOTE_BUILD_SRC_DOCS_DIR="$REMOTE_BUILD_SRC_DIR/docs"

REMOTE_LOGS_DIR="$REMOTE_BASE_DIR/logs"
REMOTE_RUN_DIR="$REMOTE_BASE_DIR/run"
REMOTE_SCRIPTS_DIR="$REMOTE_BASE_DIR/scripts"

REMOTE_README_TEMPLATE_PATH="$REMOTE_BUILD_SRC_DOCS_DIR/Release_Package_README.txt"
LOCAL_README_TEMPLATE_PATH="$ROOT_DIR/docs/Release_Package_README.txt"

SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"

RSYNC_COMMON_ARGS=(
  -avz
  --delete
  --exclude="__pycache__/"
  --exclude=".pytest_cache/"
  --exclude=".git/"
  --exclude="*.pyc"
)

echo "[deploy] Root directory: $ROOT_DIR"
echo "[deploy] Artifact: $LOCAL_ARCHIVE_PATH"
echo "[deploy] Remote target: $SSH_TARGET"
echo "[deploy] Remote base dir: $REMOTE_BASE_DIR"

if [ ! -f "$LOCAL_ARCHIVE_PATH" ]; then
  echo "[deploy][ERROR] Missing release artifact: $LOCAL_ARCHIVE_PATH" >&2
  echo "[deploy][ERROR] Run python scripts/release.py first." >&2
  exit 1
fi

if [ ! -f "$LOCAL_README_TEMPLATE_PATH" ]; then
  echo "[deploy][ERROR] Missing package README template: $LOCAL_README_TEMPLATE_PATH" >&2
  exit 1
fi

echo "[deploy] Creating remote directory structure..."
ssh "$SSH_TARGET" "
  mkdir -p \
    $REMOTE_APP_DIR \
    $REMOTE_PACKAGES_DIR \
    $REMOTE_DOWNLOADS_DIR \
    $REMOTE_BUILD_SRC_DIR \
    $REMOTE_BUILD_SRC_DOCS_DIR \
    $REMOTE_LOGS_DIR \
    $REMOTE_RUN_DIR \
    $REMOTE_SCRIPTS_DIR
"

echo "[deploy] Syncing api/ -> $REMOTE_APP_DIR/api/"
rsync "${RSYNC_COMMON_ARGS[@]}" "$ROOT_DIR/api/" "$SSH_TARGET:$REMOTE_APP_DIR/api/"

echo "[deploy] Syncing web/ -> $REMOTE_APP_DIR/web/"
rsync "${RSYNC_COMMON_ARGS[@]}" "$ROOT_DIR/web/" "$SSH_TARGET:$REMOTE_APP_DIR/web/"

echo "[deploy] Syncing scripts/ -> $REMOTE_SCRIPTS_DIR/"
rsync "${RSYNC_COMMON_ARGS[@]}" "$ROOT_DIR/scripts/" "$SSH_TARGET:$REMOTE_SCRIPTS_DIR/"

echo "[deploy] Syncing remote build sources -> $REMOTE_BUILD_SRC_DIR/"
rsync "${RSYNC_COMMON_ARGS[@]}" "$ROOT_DIR/bin/" "$SSH_TARGET:$REMOTE_BUILD_SRC_DIR/bin/"
rsync "${RSYNC_COMMON_ARGS[@]}" "$ROOT_DIR/engine/" "$SSH_TARGET:$REMOTE_BUILD_SRC_DIR/engine/"

echo "[deploy] Syncing package README template -> $REMOTE_README_TEMPLATE_PATH"
rsync -avz \
  "$LOCAL_README_TEMPLATE_PATH" \
  "$SSH_TARGET:$REMOTE_README_TEMPLATE_PATH"

echo "[deploy] Removing legacy source directories from remote app..."
ssh "$SSH_TARGET" "
  rm -rf \
    $REMOTE_APP_DIR/engine \
    $REMOTE_APP_DIR/docs
"

echo "[deploy] Building server-compatible package on remote host..."
ssh "$SSH_TARGET" "
  chmod +x \
    $REMOTE_SCRIPTS_DIR/build_remote_package.sh \
    $REMOTE_SCRIPTS_DIR/start_server.sh \
    $REMOTE_SCRIPTS_DIR/stop_server.sh &&
  $REMOTE_SCRIPTS_DIR/build_remote_package.sh
"

echo "[deploy] Restarting remote single-port web service on 8010..."
ssh "$SSH_TARGET" "
  $REMOTE_SCRIPTS_DIR/stop_server.sh &&
  $REMOTE_SCRIPTS_DIR/start_server.sh
"

echo "[deploy] Deployment files copied successfully."
echo "[deploy] Remote web port: 8010"
echo "[deploy] Verify with: bash scripts/check_server.sh"
