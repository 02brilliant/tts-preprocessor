#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)"
PROJECT_PYTHON="$ROOT_DIR/.venv/bin/python"
DEPLOY_SERVER_SCRIPT="$ROOT_DIR/scripts/deploy_server.sh"
PACKAGED_PATHS=(
  engine
  bin
  LLM
  tts_preprocessor.spec
  tts_preprocessor_simplified.spec
  tts_preprocessor_llm_minimal.spec
  tts_preprocessor_llm_natural.spec
  scripts/probes
)

if [[ ! -x "$PROJECT_PYTHON" ]]; then
  echo "[deploy-gates][ERROR] Missing project Python interpreter: $PROJECT_PYTHON" >&2
  exit 1
fi
if [[ ! -f "$DEPLOY_SERVER_SCRIPT" ]]; then
  echo "[deploy-gates][ERROR] Missing deploy script: $DEPLOY_SERVER_SCRIPT" >&2
  exit 1
fi
if ! git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[deploy-gates][ERROR] $ROOT_DIR is not a git worktree." >&2
  exit 1
fi

cd "$ROOT_DIR"

commit_packaged_worktree_if_needed() {
  if [[ "${DEPLOY_SKIP_COMMIT:-0}" == "1" ]]; then
    echo "[deploy-gates] Skipping packaged worktree commit (DEPLOY_SKIP_COMMIT=1)."
    return 0
  fi

  local packaged_status
  packaged_status="$(
    git -C "$ROOT_DIR" status --porcelain --untracked-files=all -- "${PACKAGED_PATHS[@]}"
  )"
  if [[ -z "$packaged_status" ]]; then
    echo "[deploy-gates] Packaged worktree is clean; no pre-deploy commit needed."
    return 0
  fi

  local commit_message="${DEPLOY_COMMIT_MESSAGE:-deploy: sync packaged worktree for release}"
  echo "[deploy-gates] Committing packaged worktree changes before deployment..."
  printf '%s\n' "$packaged_status"
  git -C "$ROOT_DIR" add -- "${PACKAGED_PATHS[@]}"
  if git -C "$ROOT_DIR" diff --cached --quiet; then
    echo "[deploy-gates][ERROR] Packaged paths looked dirty but nothing was staged." >&2
    exit 1
  fi
  if ! git -C "$ROOT_DIR" commit -m "$commit_message"; then
    echo "[deploy-gates][ERROR] Pre-deploy git commit failed." >&2
    exit 1
  fi
  echo "[deploy-gates][OK] Pre-deploy commit created: $(git -C "$ROOT_DIR" rev-parse --short HEAD)"
}

echo "[deploy-gates] Running integrated deployment gates..."
commit_packaged_worktree_if_needed
bash "$DEPLOY_SERVER_SCRIPT"

if [[ "${DEPLOY_EXTERNAL_API_PROBE:-1}" == "1" ]]; then
  SERVER_HOST="${DEPLOY_SERVER_HOST:-10.20.10.162}"
  SERVER_PORT="${DEPLOY_SERVER_PORT:-8010}"
  API_BASE="http://${SERVER_HOST}:${SERVER_PORT}"
  echo "[deploy-gates] Running external API core semantic probes via ${API_BASE}..."
  if ! PYTHONPATH="$ROOT_DIR" "$PROJECT_PYTHON" \
    "$ROOT_DIR/scripts/probes/run_semantic_probes.py" \
    --suite core \
    --runtime api \
    --api "$API_BASE"; then
    echo "[deploy-gates][ERROR] External API semantic probes failed." >&2
    exit 1
  fi
  echo "[deploy-gates][OK] External API semantic probes passed."
else
  echo "[deploy-gates] Skipping external API probes (DEPLOY_EXTERNAL_API_PROBE=0)."
fi

echo "[deploy-gates][OK] Deployment gates completed successfully."
