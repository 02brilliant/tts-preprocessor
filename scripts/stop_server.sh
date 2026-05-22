#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${TTS_SERVER_RUN_DIR:-$ROOT_DIR/run}"
PID_FILE="$RUN_DIR/tts_web_service.pid"

stop_pid() {
  local pid="$1"
  if [[ -z "${pid:-}" ]]; then
    return 0
  fi
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      if ! kill -0 "$pid" 2>/dev/null; then
        return 0
      fi
      sleep 1
    done
    kill -9 "$pid" 2>/dev/null || true
  fi
}

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  stop_pid "$PID"
  rm -f "$PID_FILE"
fi

pkill -f "python3 -m api.server" 2>/dev/null || true
pkill -f "python -m api.server" 2>/dev/null || true
pkill -f "python3 api/server.py" 2>/dev/null || true
pkill -f "python api/server.py" 2>/dev/null || true
pkill -f "python3 -m uvicorn api.server:app" 2>/dev/null || true
pkill -f "python3 -m http.server 8010" 2>/dev/null || true

echo "Server stopped."
