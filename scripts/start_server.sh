#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -d "$ROOT_DIR/api" && -d "$ROOT_DIR/web" && -d "$ROOT_DIR/packages" ]]; then
  APP_DIR="$ROOT_DIR"
  BASE_DIR="$ROOT_DIR"
else
  APP_DIR="$ROOT_DIR/app"
  BASE_DIR="$ROOT_DIR"
fi

if [[ ! -d "$APP_DIR/api" || ! -d "$APP_DIR/web" || ! -d "$APP_DIR/packages" ]]; then
  echo "Missing app directories under: $APP_DIR" >&2
  exit 1
fi

LOG_DIR="${TTS_SERVER_LOG_DIR:-$BASE_DIR/logs}"
RUN_DIR="${TTS_SERVER_RUN_DIR:-$BASE_DIR/run}"
HOST="${TTS_PREPROCESSOR_HOST:-0.0.0.0}"
PORT="${TTS_PREPROCESSOR_PORT:-8010}"
DEFAULT_PYTHON_BIN="python3"
if [[ -x "$BASE_DIR/.venv/bin/python" ]]; then
  DEFAULT_PYTHON_BIN="$BASE_DIR/.venv/bin/python"
elif [[ -x "$APP_DIR/.venv/bin/python" ]]; then
  DEFAULT_PYTHON_BIN="$APP_DIR/.venv/bin/python"
fi
PYTHON_BIN="${TTS_SERVER_PYTHON_BIN:-$DEFAULT_PYTHON_BIN}"
PID_FILE="$RUN_DIR/tts_web_service.pid"
LOG_FILE="$LOG_DIR/tts_web_service.log"
LLM_ENV_FILE="${TTS_LLM_ENV_FILE:-$BASE_DIR/config/llm.env}"

mkdir -p "$LOG_DIR" "$RUN_DIR"

if [[ -n "${TTS_PREPROCESSOR_BINARY:-}" ]]; then
  LATEST_BINARY="$TTS_PREPROCESSOR_BINARY"
else
  LATEST_BINARY="$APP_DIR/packages/tts-preprocessor/tts-preprocessor"
  if [[ ! -f "$LATEST_BINARY" ]]; then
    echo "No packaged binary found at $LATEST_BINARY" >&2
    exit 1
  fi
fi

if [[ -f "$PID_FILE" ]]; then
  EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${EXISTING_PID:-}" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    echo "Server already running with PID $EXISTING_PID" >&2
    exit 1
  fi
  rm -f "$PID_FILE"
fi

if [[ ! -r "$LLM_ENV_FILE" ]]; then
  echo "Missing readable LLM environment file: $LLM_ENV_FILE" >&2
  echo "Configure at least one LLM provider in this file before starting." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$LLM_ENV_FILE"
set +a

LOCAL_LLM_CONFIGURED=false
GEMINI_LLM_CONFIGURED=false
OPENAI_LLM_CONFIGURED=false
VLLM_LLM_CONFIGURED=false
if [[ -n "${LOCAL_LLM_BASE_URL:-}" && -n "${LOCAL_LLM_TOKEN:-}" ]]; then
  LOCAL_LLM_CONFIGURED=true
fi
if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  GEMINI_LLM_CONFIGURED=true
fi
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  OPENAI_LLM_CONFIGURED=true
fi
if [[ -n "${VLLM_BASE_URL:-}" && -n "${VLLM_TOKEN:-}" ]]; then
  VLLM_LLM_CONFIGURED=true
fi
if [[ "$LOCAL_LLM_CONFIGURED" != true \
  && "$GEMINI_LLM_CONFIGURED" != true \
  && "$OPENAI_LLM_CONFIGURED" != true \
  && "$VLLM_LLM_CONFIGURED" != true ]]; then
  echo "No complete LLM provider configuration was found." >&2
  echo "Configure local LLM credentials, GEMINI_API_KEY, OPENAI_API_KEY, or vLLM credentials before starting." >&2
  exit 1
fi

cd "$APP_DIR"
nohup env \
  TTS_PREPROCESSOR_HOST="$HOST" \
  TTS_PREPROCESSOR_PORT="$PORT" \
  TTS_PREPROCESSOR_BINARY="$LATEST_BINARY" \
  "$PYTHON_BIN" -m api.server >"$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

for _ in $(seq 1 20); do
  if curl -fsS "http://127.0.0.1:${PORT}/web/" >/dev/null 2>&1; then
    echo "Server started: PID=$SERVER_PID PORT=$PORT BINARY=$LATEST_BINARY"
    exit 0
  fi
  sleep 1
done

echo "Server failed to start. Log: $LOG_FILE" >&2
exit 1
