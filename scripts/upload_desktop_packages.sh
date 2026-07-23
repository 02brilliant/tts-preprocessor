#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WINDOWS_ARCHIVE="$ROOT_DIR/downloads/tts-preprocessor-windows.zip"
SSH_TARGET="brilliant@10.20.10.162"
# The quoted tilde is intentionally preserved for scp/SSH remote expansion.
# shellcheck disable=SC2088
REMOTE_DOWNLOADS_DIR="~/tts-preprocessor/app/downloads"
REMOTE_TEMP_PATH="$REMOTE_DOWNLOADS_DIR/.tts-preprocessor-windows.zip.upload.$$"
REMOTE_FINAL_PATH="$REMOTE_DOWNLOADS_DIR/tts-preprocessor-windows.zip"
HTTP_URL="http://10.20.10.162:8010/downloads/tts-preprocessor-windows.zip"
VALIDATE_ONLY=false
PLATFORM=""

usage() {
  echo "Usage: bash scripts/upload_desktop_packages.sh --platform windows [--validate-only]"
}

validate_windows_archive() (
  set -euo pipefail
  local extract_dir
  local contents
  local expected

  if [[ ! -f "$WINDOWS_ARCHIVE" ]]; then
    echo "[windows-upload][ERROR] Missing Windows ZIP: $WINDOWS_ARCHIVE" >&2
    return 1
  fi
  unzip -tq "$WINDOWS_ARCHIVE"
  contents="$(unzip -Z1 "$WINDOWS_ARCHIVE" | LC_ALL=C sort)"
  expected=$'README.txt\ntts-preprocessor.exe'
  if [[ "$contents" != "$expected" ]]; then
    echo "[windows-upload][ERROR] Unexpected Windows ZIP contents:" >&2
    printf '%s\n' "$contents" >&2
    return 1
  fi

  extract_dir="$(mktemp -d)"
  trap 'rm -rf -- "$extract_dir"' EXIT
  unzip -q "$WINDOWS_ARCHIVE" -d "$extract_dir"
  if [[ ! -f "$extract_dir/README.txt" \
    || ! -f "$extract_dir/tts-preprocessor.exe" \
    || -L "$extract_dir/README.txt" \
    || -L "$extract_dir/tts-preprocessor.exe" \
    || -n "$(find "$extract_dir" -type l -print -quit)" ]]; then
    echo "[windows-upload][ERROR] Windows ZIP payload is missing or contains a symlink." >&2
    return 1
  fi
  echo "[windows-upload][OK] Local ZIP validated: $WINDOWS_ARCHIVE"
)

cleanup_remote_temp() {
  ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_TEMP_PATH" <<'REMOTE'
set -euo pipefail
temp_path="$1"
case "$temp_path" in
  "~/"*) temp_path="$HOME/${temp_path#\~/}" ;;
esac
rm -f -- "$temp_path"
REMOTE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "[windows-upload][ERROR] --platform requires a value." >&2
        usage >&2
        exit 2
      fi
      if [[ -n "$PLATFORM" ]]; then
        echo "[windows-upload][ERROR] --platform may be specified only once." >&2
        exit 2
      fi
      PLATFORM="$2"
      shift 2
      ;;
    --validate-only)
      if [[ "$VALIDATE_ONLY" == true ]]; then
        echo "[windows-upload][ERROR] --validate-only may be specified only once." >&2
        exit 2
      fi
      VALIDATE_ONLY=true
      shift
      ;;
    *)
      echo "[windows-upload][ERROR] Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$PLATFORM" != "windows" ]]; then
  echo "[windows-upload][ERROR] This script requires --platform windows." >&2
  usage >&2
  exit 2
fi

for command_name in unzip sort mktemp find; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "[windows-upload][ERROR] Missing required local command: $command_name" >&2
    exit 1
  fi
done
validate_windows_archive

if [[ "$VALIDATE_ONLY" == true ]]; then
  echo "[windows-upload][OK] Validation-only mode completed."
  exit 0
fi

for command_name in ssh scp curl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "[windows-upload][ERROR] Missing required upload command: $command_name" >&2
    exit 1
  fi
done

echo "[windows-upload] Uploading to temporary path: $REMOTE_TEMP_PATH"
if ! scp -- "$WINDOWS_ARCHIVE" "$SSH_TARGET:$REMOTE_TEMP_PATH"; then
  cleanup_remote_temp >/dev/null 2>&1 || true
  echo "[windows-upload][ERROR] SCP failed; the existing Windows ZIP was not replaced." >&2
  exit 1
fi

if ! ssh -- "$SSH_TARGET" bash -s -- \
  "$REMOTE_TEMP_PATH" \
  "$REMOTE_FINAL_PATH" <<'REMOTE'
set -euo pipefail
temp_path="$1"
final_path="$2"
case "$temp_path" in
  "~/"*) temp_path="$HOME/${temp_path#\~/}" ;;
esac
case "$final_path" in
  "~/"*) final_path="$HOME/${final_path#\~/}" ;;
esac
cleanup_temp() {
  rm -f -- "$temp_path"
}
trap cleanup_temp EXIT
unzip -tq "$temp_path"
contents="$(unzip -Z1 "$temp_path" | LC_ALL=C sort)"
expected=$'README.txt\ntts-preprocessor.exe'
[[ "$contents" == "$expected" ]] || {
  echo "[windows-upload][ERROR] Unexpected uploaded Windows ZIP contents." >&2
  exit 1
}
mv -f -- "$temp_path" "$final_path"
trap - EXIT
REMOTE
then
  cleanup_remote_temp >/dev/null 2>&1 || true
  echo "[windows-upload][ERROR] Remote ZIP validation or publish failed." >&2
  exit 1
fi

VERIFY_URL="${HTTP_URL}?verify=$(date +%s)-$$"
HTTP_STATUS="$(
  curl -sS -I -o /dev/null -w '%{http_code}' \
    -H "Cache-Control: no-cache" \
    -- "$VERIFY_URL"
)"
if [[ "$HTTP_STATUS" != "200" ]]; then
  echo "[windows-upload][ERROR] Windows download returned HTTP $HTTP_STATUS" >&2
  exit 1
fi

echo "[windows-upload][OK] Published: tts-preprocessor-windows.zip"
