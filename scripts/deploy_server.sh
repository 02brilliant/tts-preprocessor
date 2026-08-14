#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)"
PROJECT_PYTHON="$ROOT_DIR/.venv/bin/python"
PROJECT_PYINSTALLER="$ROOT_DIR/.venv/bin/pyinstaller"
REQUIRED_PYTHON_SERIES="3.13"
MACOS_BUILD_SCRIPT="$ROOT_DIR/scripts/build_macos_package.sh"
REMOTE_BUILD_SCRIPT="$ROOT_DIR/scripts/build_remote_package.sh"
WINDOWS_UPLOAD_SCRIPT="$ROOT_DIR/scripts/upload_desktop_packages.sh"
START_SERVER_SCRIPT="$ROOT_DIR/scripts/start_server.sh"
STOP_SERVER_SCRIPT="$ROOT_DIR/scripts/stop_server.sh"
CHECK_SERVER_SCRIPT="$ROOT_DIR/scripts/check_server.sh"
LOCAL_SEMANTIC_PROBES_DIR="$ROOT_DIR/scripts/probes"
LOCAL_SPEC_PATH="$ROOT_DIR/tts_preprocessor.spec"
LOCAL_LLM_STAGE_SPEC_PATH="$ROOT_DIR/tts_llm_stage.spec"
LOCAL_ENTRYPOINT_PATH="$ROOT_DIR/bin/build_binary_entrypoint.py"
LOCAL_LLM_STAGE_ENTRYPOINT_PATH="$ROOT_DIR/bin/build_llm_stage_entrypoint.py"
LOCAL_README_TEMPLATE_PATH="$ROOT_DIR/docs/Release_Package_README.txt"
LOCAL_MACOS_ARCHIVE="$ROOT_DIR/downloads/tts-preprocessor-macos.zip"

REMOTE_USER="brilliant"
REMOTE_HOST="10.20.10.162"
SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"
# The quoted tilde is intentionally preserved for remote shell expansion.
# shellcheck disable=SC2088
REMOTE_BASE_DIR="~/tts-preprocessor"
REMOTE_APP_DIR="$REMOTE_BASE_DIR/app"
REMOTE_LLM_DIR="$REMOTE_APP_DIR/LLM"
REMOTE_DOWNLOADS_DIR="$REMOTE_APP_DIR/downloads"
REMOTE_BUILD_SRC_DIR="$REMOTE_BASE_DIR/buildsrc"
REMOTE_BUILD_SRC_DOCS_DIR="$REMOTE_BUILD_SRC_DIR/docs"
REMOTE_BUILD_SRC_PROBES_DIR="$REMOTE_BUILD_SRC_DIR/scripts/probes"
REMOTE_BUILD_SRC_DEPLOY_SCRIPTS_DIR="$REMOTE_BUILD_SRC_DIR/deploy-scripts"
REMOTE_SCRIPTS_DIR="$REMOTE_BASE_DIR/scripts"

DEPLOY_ID=""
DEPLOY_LOG_DIR="$ROOT_DIR/build/deploy-logs"
LINUX_BUILD_LOG=""
MACOS_BUILD_LOG=""
REMOTE_MACOS_TEMP=""
LINUX_BUILD_PID=""
MACOS_BUILD_PID=""
PARALLEL_BUILDS_ACTIVE=false

RSYNC_COMMON_ARGS=(
  -avz
  --delete
  --exclude="__pycache__/"
  --exclude=".pytest_cache/"
  --exclude=".git/"
  --exclude=".venv/"
  --exclude="build/"
  --exclude="dist/"
  --exclude="*.pyc"
)

run_remote_build_action() {
  local action="$1"

  ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_BASE_DIR" "$action" "$DEPLOY_ID" <<'REMOTE'
set -euo pipefail
remote_base_dir="$1"
action="$2"
deploy_id="$3"
case "$remote_base_dir" in
  "~/"*) remote_base_dir="$HOME/${remote_base_dir#\~/}" ;;
esac
bash "$remote_base_dir/scripts/build_remote_package.sh" "$action" "$deploy_id"
REMOTE
}

best_effort_remote_cleanup() {
  if ! run_remote_build_action cleanup; then
    echo "[deploy][WARN] Remote staging/buildsrc cleanup failed for deploy ID: $DEPLOY_ID" >&2
    echo "[deploy][WARN] Retry after inspection with:" >&2
    echo "  ssh $SSH_TARGET bash ~/tts-preprocessor/scripts/build_remote_package.sh cleanup $DEPLOY_ID" >&2
    return 1
  fi
}

validate_local_macos_archive() (
  set -euo pipefail
  local extract_dir
  local contents
  local expected

  if [[ ! -f "$LOCAL_MACOS_ARCHIVE" ]]; then
    echo "[deploy][ERROR] Fresh macOS archive is missing: $LOCAL_MACOS_ARCHIVE" >&2
    return 1
  fi
  unzip -tq "$LOCAL_MACOS_ARCHIVE"
  contents="$(unzip -Z1 "$LOCAL_MACOS_ARCHIVE" | LC_ALL=C sort)"
  expected=$'README.txt\ntts-llm-stage\ntts-preprocessor'
  if [[ "$contents" != "$expected" ]]; then
    echo "[deploy][ERROR] Unexpected macOS ZIP contents:" >&2
    printf '%s\n' "$contents" >&2
    return 1
  fi

  extract_dir="$(mktemp -d)"
  trap 'rm -rf -- "$extract_dir"' EXIT
  unzip -q "$LOCAL_MACOS_ARCHIVE" -d "$extract_dir"
  if [[ ! -f "$extract_dir/README.txt" \
    || ! -x "$extract_dir/tts-preprocessor" \
    || ! -x "$extract_dir/tts-llm-stage" \
    || -L "$extract_dir/README.txt" \
    || -L "$extract_dir/tts-preprocessor" \
    || -L "$extract_dir/tts-llm-stage" \
    || -n "$(find "$extract_dir" -type l -print -quit)" ]]; then
    echo "[deploy][ERROR] macOS ZIP payload is missing, non-executable, or contains a symlink." >&2
    return 1
  fi
)

cleanup_failed_macos_upload() {
  ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_MACOS_TEMP" <<'REMOTE'
set -euo pipefail
temp_path="$1"
case "$temp_path" in
  "~/"*) temp_path="$HOME/${temp_path#\~/}" ;;
esac
rm -f -- "$temp_path"
REMOTE
}

terminate_parallel_builds() {
  local signal_name="$1"
  local child_pid

  trap - INT TERM
  if [[ "$PARALLEL_BUILDS_ACTIVE" != true ]]; then
    exit 130
  fi

  echo "[deploy][ERROR] Received $signal_name; terminating parallel build children." >&2
  for child_pid in "$LINUX_BUILD_PID" "$MACOS_BUILD_PID"; do
    if [[ -n "$child_pid" ]] && kill -0 "$child_pid" 2>/dev/null; then
      # Job control normally gives each background build its own process group.
      # Some non-interactive shells do not, so fall back to the direct child PID
      # rather than leaving the deployment process blocked in wait.
      kill -TERM -- "-$child_pid" 2>/dev/null || kill -TERM -- "$child_pid" 2>/dev/null || true
    fi
  done
  set +e
  for child_pid in "$LINUX_BUILD_PID" "$MACOS_BUILD_PID"; do
    if [[ -n "$child_pid" ]]; then
      wait "$child_pid" 2>/dev/null
    fi
  done
  set -e
  PARALLEL_BUILDS_ACTIVE=false
  LINUX_BUILD_PID=""
  MACOS_BUILD_PID=""
  set +m
  best_effort_remote_cleanup || true
  echo "[deploy][ERROR] Publish, server stop, desktop deletion, upload, and server start were not run." >&2
  exit 130
}

stop_remote_server() {
  ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_BASE_DIR" <<'REMOTE'
set -euo pipefail
remote_base_dir="$1"
case "$remote_base_dir" in
  "~/"*) remote_base_dir="$HOME/${remote_base_dir#\~/}" ;;
esac
bash "$remote_base_dir/scripts/stop_server.sh"
REMOTE
}

clear_remote_python_bytecode() {
  ssh -- "$SSH_TARGET" bash -s -- \
    "$REMOTE_APP_DIR/api" \
    "$REMOTE_LLM_DIR" <<'REMOTE'
set -euo pipefail
api_dir="$1"
llm_dir="$2"

for app_dir in "$api_dir" "$llm_dir"; do
  [[ -d "$app_dir" ]] || {
    echo "[deploy][ERROR] Missing expected application directory: $app_dir" >&2
    exit 1
  }
done

find "$api_dir" "$llm_dir" \
  -type d \
  -name __pycache__ \
  -prune \
  -exec rm -rf -- {} +
REMOTE
}

start_remote_server() {
  ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_BASE_DIR" <<'REMOTE'
set -euo pipefail
remote_base_dir="$1"
case "$remote_base_dir" in
  "~/"*) remote_base_dir="$HOME/${remote_base_dir#\~/}" ;;
esac
bash "$remote_base_dir/scripts/start_server.sh"
REMOTE
}

run_remote_api_semantic_probes() {
  ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_BASE_DIR" <<'REMOTE'
set -euo pipefail
remote_base_dir="$1"
case "$remote_base_dir" in
  "~/"*) remote_base_dir="$HOME/${remote_base_dir#\~/}" ;;
esac
runtime_python="$remote_base_dir/.venv/bin/python"
semantic_probe_runner="$remote_base_dir/buildsrc/scripts/probes/run_semantic_probes.py"

[[ -x "$runtime_python" ]] || {
  echo "[deploy][ERROR] Missing API probe Python: $runtime_python" >&2
  exit 1
}
[[ -f "$semantic_probe_runner" ]] || {
  echo "[deploy][ERROR] Missing API semantic probe runner: $semantic_probe_runner" >&2
  exit 1
}

"$runtime_python" "$semantic_probe_runner" \
  --suite core \
  --runtime api \
  --api http://127.0.0.1:8010
REMOTE
}

install_remote_server_scripts() {
  ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_BASE_DIR" <<'REMOTE'
set -euo pipefail
remote_base_dir="$1"
case "$remote_base_dir" in
  "~/"*) remote_base_dir="$HOME/${remote_base_dir#\~/}" ;;
esac
staged_scripts_dir="$remote_base_dir/buildsrc/deploy-scripts"
scripts_dir="$remote_base_dir/scripts"
for script_name in start_server.sh stop_server.sh; do
  [[ -f "$staged_scripts_dir/$script_name" ]] || {
    echo "[deploy][ERROR] Missing staged server script: $script_name" >&2
    exit 1
  }
done
cp "$staged_scripts_dir/start_server.sh" "$scripts_dir/start_server.sh"
cp "$staged_scripts_dir/stop_server.sh" "$scripts_dir/stop_server.sh"
chmod +x "$scripts_dir/start_server.sh" "$scripts_dir/stop_server.sh"
REMOTE
}

echo "[deploy] Root directory: $ROOT_DIR"
echo "[deploy] Remote target: $SSH_TARGET"

LOCAL_OS="$(uname -s)"
LOCAL_ARCH="$(uname -m)"
if [[ "$LOCAL_OS" != "Darwin" || "$LOCAL_ARCH" != "arm64" ]]; then
  echo "[deploy][ERROR] Integrated Linux + macOS deployment requires Darwin arm64." >&2
  echo "[deploy][ERROR] Detected: OS=$LOCAL_OS ARCH=$LOCAL_ARCH" >&2
  exit 1
fi

for required_local_command in \
  bash ssh scp rsync curl file zip unzip shasum git date find mktemp sort; do
  if ! command -v "$required_local_command" >/dev/null 2>&1; then
    echo "[deploy][ERROR] Missing required local command: $required_local_command" >&2
    exit 1
  fi
done

for required_local_file in \
  "$PROJECT_PYTHON" \
  "$PROJECT_PYINSTALLER" \
  "$LOCAL_SPEC_PATH" \
  "$LOCAL_LLM_STAGE_SPEC_PATH" \
  "$LOCAL_ENTRYPOINT_PATH" \
  "$LOCAL_LLM_STAGE_ENTRYPOINT_PATH" \
  "$LOCAL_README_TEMPLATE_PATH" \
  "$REMOTE_BUILD_SCRIPT" \
  "$MACOS_BUILD_SCRIPT" \
  "$WINDOWS_UPLOAD_SCRIPT" \
  "$START_SERVER_SCRIPT" \
  "$STOP_SERVER_SCRIPT" \
  "$CHECK_SERVER_SCRIPT"; do
  if [[ ! -f "$required_local_file" || ! -r "$required_local_file" ]]; then
    echo "[deploy][ERROR] Missing local deployment prerequisite: $required_local_file" >&2
    exit 1
  fi
done

for required_llm_file in \
  "$ROOT_DIR/LLM/__init__.py" \
  "$ROOT_DIR/LLM/client.py" \
  "$ROOT_DIR/LLM/config.py" \
  "$ROOT_DIR/LLM/gemini_client.py" \
  "$ROOT_DIR/LLM/openai_client.py" \
  "$ROOT_DIR/LLM/vllm_client.py" \
  "$ROOT_DIR/LLM/paragraph_parallel.py" \
  "$ROOT_DIR/LLM/cli_protocol.py" \
  "$ROOT_DIR/LLM/models.json" \
  "$ROOT_DIR/LLM/prompt_template.py" \
  "$ROOT_DIR/LLM/response_validation.py" \
  "$ROOT_DIR/LLM/docs/LLM_prompt.txt"; do
  if [[ ! -f "$required_llm_file" || ! -r "$required_llm_file" ]]; then
    echo "[deploy][ERROR] Missing local LLM runtime prerequisite: $required_llm_file" >&2
    exit 1
  fi
done

if [[ ! -d "$LOCAL_SEMANTIC_PROBES_DIR" ]]; then
  echo "[deploy][ERROR] Missing local semantic probe directory: $LOCAL_SEMANTIC_PROBES_DIR" >&2
  exit 1
fi

if [[ ! -x "$PROJECT_PYTHON" || ! -x "$PROJECT_PYINSTALLER" ]]; then
  echo "[deploy][ERROR] Project Python and PyInstaller must be executable." >&2
  exit 1
fi
PROJECT_PYTHON_ARCH="$("$PROJECT_PYTHON" -c 'import platform; print(platform.machine())')"
PROJECT_PYTHON_RUNTIME="$("$PROJECT_PYTHON" -c 'import sys, sysconfig; print("%d.%d:%d" % (sys.version_info.major, sys.version_info.minor, int(bool(sysconfig.get_config_var("Py_GIL_DISABLED")))))')"
if [[ "$PROJECT_PYTHON_RUNTIME" != "$REQUIRED_PYTHON_SERIES:0" ]]; then
  echo "[deploy][ERROR] Project Python must be standard-GIL Python $REQUIRED_PYTHON_SERIES.x; got: $PROJECT_PYTHON_RUNTIME" >&2
  exit 1
fi
if [[ "$PROJECT_PYTHON_ARCH" != "arm64" ]]; then
  echo "[deploy][ERROR] Project Python must be arm64; got: $PROJECT_PYTHON_ARCH" >&2
  exit 1
fi

SOURCE_REVISION="$(git -C "$ROOT_DIR" rev-parse --short=7 HEAD)"
DEPLOY_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$$-$SOURCE_REVISION"
if [[ ! "$DEPLOY_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "[deploy][ERROR] Generated invalid deploy ID: $DEPLOY_ID" >&2
  exit 1
fi
LINUX_BUILD_LOG="$DEPLOY_LOG_DIR/linux-prepare-$DEPLOY_ID.log"
MACOS_BUILD_LOG="$DEPLOY_LOG_DIR/macos-build-$DEPLOY_ID.log"
REMOTE_MACOS_TEMP="$REMOTE_DOWNLOADS_DIR/.tts-preprocessor-macos.zip.upload-$DEPLOY_ID"
echo "[deploy] Deploy ID: $DEPLOY_ID"

echo "[deploy] Checking the existing remote Linux build environment..."
ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_BASE_DIR" <<'REMOTE'
set -euo pipefail
remote_base_dir="$1"
case "$remote_base_dir" in
  "~/"*) remote_base_dir="$HOME/${remote_base_dir#\~/}" ;;
esac
buildenv_dir="$remote_base_dir/buildenv"
runtime_python="$remote_base_dir/.venv/bin/python"
llm_env_file="$remote_base_dir/config/llm.env"
[[ -f "$remote_base_dir/scripts/stop_server.sh" ]] || {
  echo "[deploy][ERROR] Missing existing remote stop script." >&2
  exit 1
}
[[ -r "$llm_env_file" ]] || {
  echo "[deploy][ERROR] Missing readable LLM environment file: $llm_env_file" >&2
  echo "[deploy][ERROR] Configure at least one LLM provider there before deployment." >&2
  exit 1
}
for executable in \
  "$runtime_python" \
  "$buildenv_dir/bin/python" \
  "$buildenv_dir/bin/pip" \
  "$buildenv_dir/bin/pyinstaller"; do
  [[ -x "$executable" ]] || {
    echo "[deploy][ERROR] Missing existing buildenv executable: $executable" >&2
    exit 1
  }
done
for python_bin in "$runtime_python" "$buildenv_dir/bin/python"; do
  python_runtime="$("$python_bin" -c 'import sys, sysconfig; print("%d.%d:%d" % (sys.version_info.major, sys.version_info.minor, int(bool(sysconfig.get_config_var("Py_GIL_DISABLED")))))')"
  if [[ "$python_runtime" != "3.13:0" ]]; then
    echo "[deploy][ERROR] Runtime must use standard-GIL Python 3.13.x: $python_bin (got $python_runtime)" >&2
    exit 1
  fi
done
for command_name in \
  bash python3 mkdir rm mv cp chmod find sort stat sha256sum unzip rsync; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "[deploy][ERROR] Missing required remote command: $command_name" >&2
    exit 1
  }
done
REMOTE

echo "[deploy] Preparing isolated remote buildsrc..."
ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_BASE_DIR" <<'REMOTE'
set -euo pipefail
remote_base_dir="$1"
case "$remote_base_dir" in
  "~/"*) remote_base_dir="$HOME/${remote_base_dir#\~/}" ;;
esac
rm -rf -- "$remote_base_dir/buildsrc"
mkdir -p \
  "$remote_base_dir/app/api" \
  "$remote_base_dir/app/LLM/docs" \
  "$remote_base_dir/app/web" \
  "$remote_base_dir/app/packages" \
  "$remote_base_dir/app/downloads" \
  "$remote_base_dir/buildsrc/bin" \
  "$remote_base_dir/buildsrc/docs" \
  "$remote_base_dir/buildsrc/engine" \
  "$remote_base_dir/buildsrc/deploy-scripts" \
  "$remote_base_dir/buildsrc/scripts/probes" \
  "$remote_base_dir/scripts" \
  "$remote_base_dir/logs" \
  "$remote_base_dir/run"
REMOTE

echo "[deploy] Syncing application and required Linux build sources..."
rsync "${RSYNC_COMMON_ARGS[@]}" "$ROOT_DIR/api/" "$SSH_TARGET:$REMOTE_APP_DIR/api/"
rsync "${RSYNC_COMMON_ARGS[@]}" "$ROOT_DIR/web/" "$SSH_TARGET:$REMOTE_APP_DIR/web/"
rsync "${RSYNC_COMMON_ARGS[@]}" \
  --exclude="tests/" \
  --exclude="docs/info_Local_LLM_server.txt" \
  "$ROOT_DIR/LLM/" "$SSH_TARGET:$REMOTE_LLM_DIR/"
rsync "${RSYNC_COMMON_ARGS[@]}" \
  --exclude="tests/" \
  --exclude="docs/info_Local_LLM_server.txt" \
  "$ROOT_DIR/LLM/" "$SSH_TARGET:$REMOTE_BUILD_SRC_DIR/LLM/"
rsync "${RSYNC_COMMON_ARGS[@]}" "$ROOT_DIR/engine/" "$SSH_TARGET:$REMOTE_BUILD_SRC_DIR/engine/"
rsync -avz "$LOCAL_ENTRYPOINT_PATH" "$SSH_TARGET:$REMOTE_BUILD_SRC_DIR/bin/build_binary_entrypoint.py"
rsync -avz "$LOCAL_LLM_STAGE_ENTRYPOINT_PATH" "$SSH_TARGET:$REMOTE_BUILD_SRC_DIR/bin/build_llm_stage_entrypoint.py"
rsync -avz "$LOCAL_SPEC_PATH" "$SSH_TARGET:$REMOTE_BUILD_SRC_DIR/tts_preprocessor.spec"
rsync -avz "$LOCAL_LLM_STAGE_SPEC_PATH" "$SSH_TARGET:$REMOTE_BUILD_SRC_DIR/tts_llm_stage.spec"
rsync -avz \
  "$LOCAL_README_TEMPLATE_PATH" \
  "$SSH_TARGET:$REMOTE_BUILD_SRC_DOCS_DIR/Release_Package_README.txt"
rsync "${RSYNC_COMMON_ARGS[@]}" \
  "$LOCAL_SEMANTIC_PROBES_DIR/" \
  "$SSH_TARGET:$REMOTE_BUILD_SRC_PROBES_DIR/"
rsync -avz "$REMOTE_BUILD_SCRIPT" "$SSH_TARGET:$REMOTE_SCRIPTS_DIR/build_remote_package.sh"
rsync -avz \
  "$START_SERVER_SCRIPT" \
  "$SSH_TARGET:$REMOTE_BUILD_SRC_DEPLOY_SCRIPTS_DIR/start_server.sh"
rsync -avz \
  "$STOP_SERVER_SCRIPT" \
  "$SSH_TARGET:$REMOTE_BUILD_SRC_DEPLOY_SCRIPTS_DIR/stop_server.sh"

mkdir -p "$DEPLOY_LOG_DIR"
: > "$LINUX_BUILD_LOG"
: > "$MACOS_BUILD_LOG"

echo "[deploy] Starting Linux prepare and macOS build in parallel."
set -m
run_remote_build_action prepare >"$LINUX_BUILD_LOG" 2>&1 &
LINUX_BUILD_PID=$!
bash "$MACOS_BUILD_SCRIPT" >"$MACOS_BUILD_LOG" 2>&1 &
MACOS_BUILD_PID=$!
PARALLEL_BUILDS_ACTIVE=true
trap 'terminate_parallel_builds INT' INT
trap 'terminate_parallel_builds TERM' TERM

set +e
wait "$LINUX_BUILD_PID"
LINUX_BUILD_STATUS=$?
wait "$MACOS_BUILD_PID"
MACOS_BUILD_STATUS=$?
set -e
PARALLEL_BUILDS_ACTIVE=false
LINUX_BUILD_PID=""
MACOS_BUILD_PID=""
set +m
trap - INT TERM

if [[ "$LINUX_BUILD_STATUS" -ne 0 || "$MACOS_BUILD_STATUS" -ne 0 ]]; then
  best_effort_remote_cleanup || true
  echo "[deploy][ERROR] Parallel build stage failed; the existing server and production artifacts were retained." >&2
  echo "[deploy][ERROR] Linux prepare status: $LINUX_BUILD_STATUS (log: $LINUX_BUILD_LOG)" >&2
  echo "[deploy][ERROR] macOS build status: $MACOS_BUILD_STATUS (log: $MACOS_BUILD_LOG)" >&2
  echo "[deploy][ERROR] Server stop, publish, desktop deletion, upload, and server start were not run." >&2
  exit 1
fi
echo "[deploy][OK] Linux prepare and macOS build both succeeded."
echo "[deploy] Linux log: $LINUX_BUILD_LOG"
echo "[deploy] macOS log: $MACOS_BUILD_LOG"

validate_local_macos_archive

echo "[deploy] Stopping the server before Linux publish..."
if ! stop_remote_server; then
  best_effort_remote_cleanup || true
  echo "[deploy][ERROR] Server stop failed; Linux publish and desktop changes were not run." >&2
  exit 1
fi

echo "[deploy] Removing stale Python bytecode from the stopped application..."
if ! clear_remote_python_bytecode; then
  best_effort_remote_cleanup || true
  echo "[deploy][ERROR] Python bytecode cleanup failed; publish and server restart were not run." >&2
  exit 1
fi

echo "[deploy] Publishing the prepared Linux package and ZIP..."
if ! run_remote_build_action publish; then
  echo "[deploy][ERROR] Linux publish failed after the server was stopped." >&2
  echo "[deploy][ERROR] Desktop ZIP deletion, macOS upload, and server start were not run." >&2
  echo "[deploy][ERROR] The server remains stopped; fix the issue and run the full deployment again." >&2
  exit 1
fi

echo "[deploy] Installing the staged server control scripts..."
if ! install_remote_server_scripts; then
  echo "[deploy][ERROR] Linux publish succeeded, but server script installation failed." >&2
  echo "[deploy][ERROR] Desktop ZIP changes and server start were not run; run the full deployment again." >&2
  exit 1
fi

echo "[deploy] Invalidating exact stale desktop ZIPs..."
if ! ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_DOWNLOADS_DIR" <<'REMOTE'
set -euo pipefail
downloads_dir="$1"
case "$downloads_dir" in
  "~/"*) downloads_dir="$HOME/${downloads_dir#\~/}" ;;
esac
rm -f -- \
  "$downloads_dir/tts-preprocessor-macos.zip" \
  "$downloads_dir/tts-preprocessor-windows.zip"
REMOTE
then
  echo "[deploy][ERROR] Linux publish succeeded, but stale desktop ZIP deletion failed." >&2
  echo "[deploy][ERROR] macOS upload and server start were not run; run the full deployment again." >&2
  exit 1
fi

LOCAL_MACOS_SIZE="$("$PROJECT_PYTHON" -c 'import os, sys; print(os.path.getsize(sys.argv[1]))' "$LOCAL_MACOS_ARCHIVE")"
echo "[deploy] Uploading the freshly built macOS ZIP to a temporary name..."
if ! scp -- "$LOCAL_MACOS_ARCHIVE" "$SSH_TARGET:$REMOTE_MACOS_TEMP"; then
  cleanup_failed_macos_upload >/dev/null 2>&1 || true
  echo "[deploy][ERROR] Linux publish succeeded, but macOS SCP failed." >&2
  echo "[deploy][ERROR] Desktop ZIPs may be absent and the server remains stopped; run the full deployment again." >&2
  exit 1
fi

if ! ssh -- "$SSH_TARGET" bash -s -- \
  "$REMOTE_MACOS_TEMP" \
  "$REMOTE_DOWNLOADS_DIR/tts-preprocessor-macos.zip" \
  "$LOCAL_MACOS_SIZE" <<'REMOTE'
set -euo pipefail
temp_path="$1"
final_path="$2"
expected_size="$3"
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
[[ "$(stat -c '%s' "$temp_path")" == "$expected_size" ]]
unzip -tq "$temp_path"
contents="$(unzip -Z1 "$temp_path" | LC_ALL=C sort)"
expected=$'README.txt\ntts-llm-stage\ntts-preprocessor'
[[ "$contents" == "$expected" ]] || {
  echo "[deploy][ERROR] Unexpected uploaded macOS ZIP contents." >&2
  exit 1
}
mv -f -- "$temp_path" "$final_path"
trap - EXIT
REMOTE
then
  cleanup_failed_macos_upload >/dev/null 2>&1 || true
  echo "[deploy][ERROR] Linux publish succeeded, but remote macOS ZIP validation or publish failed." >&2
  echo "[deploy][ERROR] Desktop ZIPs may be absent and the server remains stopped; run the full deployment again." >&2
  exit 1
fi

echo "[deploy] Removing any accidentally served transform sources..."
if ! ssh -- "$SSH_TARGET" bash -s -- "$REMOTE_BASE_DIR" <<'REMOTE'
set -euo pipefail
remote_base_dir="$1"
case "$remote_base_dir" in
  "~/"*) remote_base_dir="$HOME/${remote_base_dir#\~/}" ;;
esac
rm -rf -- "$remote_base_dir/app/engine" "$remote_base_dir/app/docs"
REMOTE
then
  echo "[deploy][ERROR] Artifact publish succeeded, but source-free runtime cleanup failed." >&2
  echo "[deploy][ERROR] The server remains stopped; inspect the app directory and run the full deployment again." >&2
  exit 1
fi

echo "[deploy] Starting the server after Linux and macOS artifacts are ready..."
if ! start_remote_server; then
  echo "[deploy][ERROR] Server start failed." >&2
  echo "[deploy][ERROR] Linux and macOS artifacts may already be published; run the full deployment again after inspection." >&2
  exit 1
fi

echo "[deploy] Verifying Web, Linux, macOS, API docs, rule transform, and LLM transform..."
if ! bash "$CHECK_SERVER_SCRIPT"; then
  echo "[deploy][ERROR] Deployment artifacts were published and the server was started," >&2
  echo "[deploy][ERROR] but final verification failed." >&2
  echo "[deploy][ERROR] Review the server and rerun the full deployment if necessary." >&2
  exit 1
fi

echo "[deploy] Running the canonical core semantic probes through the live API..."
if ! run_remote_api_semantic_probes; then
  echo "[deploy][ERROR] The live API does not match the verified published binary semantics." >&2
  echo "[deploy][ERROR] Temporary build sources were retained for diagnosis." >&2
  echo "[deploy][ERROR] Inspect TTS_PREPROCESSOR_BINARY and rerun the full deployment." >&2
  exit 1
fi

if ! run_remote_build_action cleanup; then
  echo "[deploy][ERROR] Linux and macOS artifacts were published and verified, but temporary source cleanup failed." >&2
  echo "[deploy][ERROR] The running service was retained. Retry cleanup with:" >&2
  echo "  ssh $SSH_TARGET bash ~/tts-preprocessor/scripts/build_remote_package.sh cleanup $DEPLOY_ID" >&2
  exit 1
fi

echo "[deploy][OK] Deployment completed successfully."
echo "[deploy] Linux package: tts-preprocessor-linux.zip"
echo "[deploy] macOS package: tts-preprocessor-macos.zip"
echo "[deploy] Windows package: not built or uploaded by this deployment"
