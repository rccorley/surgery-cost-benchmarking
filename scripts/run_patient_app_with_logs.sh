#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
RUNTIME_LOG="$LOG_DIR/patient_calculator_runtime.log"
PID_FILE="$LOG_DIR/patient_calculator.pid"
PORT="${1:-8512}"
STARTUP_WAIT_SECONDS="${STARTUP_WAIT_SECONDS:-6}"

mkdir -p "$LOG_DIR"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${OLD_PID:-}" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping existing app process $OLD_PID"
    kill "$OLD_PID" || true
    sleep 1
  fi
fi

# If the requested port is already in use, stop existing listeners so restart is deterministic.
EXISTING_PORT_PIDS="$(lsof -t -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | tr '\n' ' ' || true)"
if [[ -n "${EXISTING_PORT_PIDS// }" ]]; then
  echo "Stopping existing listener(s) on port $PORT: $EXISTING_PORT_PIDS"
  for pid in $EXISTING_PORT_PIDS; do
    kill "$pid" 2>/dev/null || true
  done
  sleep 1
fi

if [[ -n "${STREAMLIT_BIN:-}" && -x "${STREAMLIT_BIN:-}" ]]; then
  STREAMLIT_BIN="$STREAMLIT_BIN"
else
  STREAMLIT_BIN="$(command -v streamlit || true)"
  if [[ -z "${STREAMLIT_BIN:-}" && -x "$ROOT/.venv/bin/streamlit" ]]; then
    STREAMLIT_BIN="$ROOT/.venv/bin/streamlit"
  fi
fi

if [[ -z "${STREAMLIT_BIN:-}" ]]; then
  echo "ERROR: streamlit executable not found." | tee -a "$RUNTIME_LOG"
  exit 1
fi

{
  echo ""
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Launching app on port $PORT"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] streamlit_bin=$STREAMLIT_BIN"
} >>"$RUNTIME_LOG"

echo "Starting Streamlit on port $PORT"
nohup "$STREAMLIT_BIN" run "$ROOT/src/patient_calculator.py" \
  --server.headless true \
  --server.port "$PORT" \
  >>"$RUNTIME_LOG" 2>&1 &

NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

# Validate that the process remains alive and actually binds the requested port.
started=0
for ((i=0; i<STARTUP_WAIT_SECONDS*10; i++)); do
  if ! kill -0 "$NEW_PID" 2>/dev/null; then
    echo "ERROR: Streamlit process $NEW_PID exited during startup." | tee -a "$RUNTIME_LOG"
    echo "Tip: check for PermissionError on socket bind or Python import errors." | tee -a "$RUNTIME_LOG"
    echo "--- Last runtime log lines ---"
    tail -n 40 "$RUNTIME_LOG" || true
    exit 1
  fi
  LISTENER_PIDS="$(lsof -t -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | tr '\n' ' ' || true)"
  if [[ " $LISTENER_PIDS " == *" $NEW_PID "* ]]; then
    started=1
    break
  fi
  sleep 0.1
done

if [[ "$started" -ne 1 ]]; then
  echo "ERROR: Streamlit did not bind localhost:$PORT within ${STARTUP_WAIT_SECONDS}s." | tee -a "$RUNTIME_LOG"
  echo "Tip: this is often a port conflict or permission/sandbox bind restriction." | tee -a "$RUNTIME_LOG"
  echo "--- Last runtime log lines ---"
  tail -n 40 "$RUNTIME_LOG" || true
  exit 1
fi

echo "PID: $NEW_PID"
echo "Runtime log: $RUNTIME_LOG"
echo "App URL: http://localhost:$PORT"
